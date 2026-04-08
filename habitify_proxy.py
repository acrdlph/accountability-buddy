"""Habitify MCP proxy server with automatic OAuth token refresh.

Sits between Claude Code (stdio transport) and the Habitify MCP server (SSE),
transparently managing Bearer token lifecycle using a stored refresh token.

Setup:
    1. Run the OAuth setup: python3 habitify_oauth_setup.py
    2. Ensure .env has HABITIFY_CLIENT_ID and HABITIFY_REFRESH_TOKEN
    3. Configure .mcp.json to use this as a stdio server
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import anyio
import httpx
from dotenv import load_dotenv
from mcp import ClientSession, types
from mcp.client.sse import sse_client
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server

# Load .env from same directory as this script
_script_dir = Path(__file__).resolve().parent
load_dotenv(_script_dir / ".env")

# Logging goes to stderr (stdout is the MCP stdio transport)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("habitify-proxy")

TOKEN_URL = "https://account.habitify.me/token"
HABITIFY_MCP_URL = "https://mcp.habitify.me/mcp"

# --- Token management ---

_access_token: str | None = None


def _invalidate_token() -> None:
    global _access_token
    _access_token = None


async def _ensure_token() -> str:
    global _access_token
    if _access_token:
        return _access_token

    client_id = os.getenv("HABITIFY_CLIENT_ID")
    refresh_token = os.getenv("HABITIFY_REFRESH_TOKEN")

    if not client_id or not refresh_token:
        raise RuntimeError(
            "HABITIFY_CLIENT_ID and HABITIFY_REFRESH_TOKEN must be set in .env. "
            "Run: python3 habitify_oauth_setup.py"
        )

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": client_id,
                "scope": "openid offline_access all",
            },
        )
        if resp.status_code != 200:
            raise RuntimeError(
                f"Token refresh failed ({resp.status_code}): {resp.text}"
            )
        _access_token = resp.json()["access_token"]
        logger.info("Access token refreshed")
        return _access_token


# --- Upstream MCP helpers ---
# Each call opens a fresh SSE connection because Habitify drops idle
# connections after ~30 seconds.


async def _upstream_list_tools(token: str) -> list[types.Tool]:
    headers = {"Authorization": f"Bearer {token}"}
    async with sse_client(HABITIFY_MCP_URL, headers=headers) as (rs, ws):
        async with ClientSession(rs, ws) as session:
            await session.initialize()
            result = await session.list_tools()
            return result.tools


async def _upstream_call_tool(
    token: str, name: str, arguments: dict
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    headers = {"Authorization": f"Bearer {token}"}
    async with sse_client(HABITIFY_MCP_URL, headers=headers) as (rs, ws):
        async with ClientSession(rs, ws) as session:
            await session.initialize()
            result = await session.call_tool(name, arguments)
            return result.content


# --- MCP Server (stdio) ---

server = Server("habitify-proxy")

# Cache upstream tool schemas so we don't re-discover on every list_tools call
_cached_tools: list[types.Tool] | None = None


async def _ensure_tools() -> list[types.Tool]:
    global _cached_tools
    if _cached_tools is not None:
        return _cached_tools

    token = await _ensure_token()
    try:
        _cached_tools = await _upstream_list_tools(token)
    except Exception:
        # Token may be stale, retry once
        _invalidate_token()
        token = await _ensure_token()
        _cached_tools = await _upstream_list_tools(token)

    logger.info(f"Discovered {len(_cached_tools)} upstream tools")
    return _cached_tools


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return await _ensure_tools()


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    arguments = arguments or {}
    token = await _ensure_token()
    try:
        return await _upstream_call_tool(token, name, arguments)
    except Exception as e:
        err_str = str(e).lower()
        if "401" in err_str or "auth" in err_str or "token" in err_str:
            logger.warning(f"Auth error on {name}, refreshing token and retrying")
            _invalidate_token()
            token = await _ensure_token()
            return await _upstream_call_tool(token, name, arguments)
        raise


# --- Entry point ---


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    anyio.run(main)
