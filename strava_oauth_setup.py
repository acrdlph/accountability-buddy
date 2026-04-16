"""One-time OAuth setup for Strava.

Walks the user through Strava's OAuth authorization code flow and stores
the resulting access + refresh tokens in .env. The strava-mcp server
auto-refreshes the access token afterwards using the refresh token.

Prerequisites:
  - Create a Strava API app at https://www.strava.com/settings/api
    - Set "Authorization Callback Domain" to: localhost
  - Put STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET in .env

Usage:
    .venv/bin/python strava_oauth_setup.py
"""

from __future__ import annotations

import os
import secrets
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import httpx
from dotenv import load_dotenv

AUTHORIZATION_URL = "https://www.strava.com/oauth/authorize"
TOKEN_URL = "https://www.strava.com/oauth/token"

# The "Authorization Callback Domain" on the Strava app must be "localhost"
# so this redirect_uri is accepted. No server actually listens — the user
# pastes the full URL back after being redirected.
REDIRECT_URI = "http://localhost/exchange_token"

# Scopes:
#   activity:read_all — read all activities (including private ones)
#   profile:read_all  — read athlete stats, shoes, zones
SCOPE = "read,activity:read_all,profile:read_all"

ENV_PATH = Path(__file__).resolve().parent / ".env"


def _build_authorization_url(client_id: str, state: str) -> str:
    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "approval_prompt": "force",
        "scope": SCOPE,
        "state": state,
    }
    return f"{AUTHORIZATION_URL}?{urlencode(params)}"


def _extract_code_from_url(callback_url: str, expected_state: str) -> str:
    parsed = urlparse(callback_url)
    params = parse_qs(parsed.query)

    if "error" in params:
        raise RuntimeError(f"Authorization failed: {params['error'][0]}")

    returned_state = params.get("state", [None])[0]
    if returned_state != expected_state:
        raise RuntimeError("State mismatch — run the setup again")

    code = params.get("code", [None])[0]
    if not code:
        raise RuntimeError("No authorization code found in the URL")

    granted_scope = params.get("scope", [""])[0]
    required = {"activity:read_all"}
    granted = set(granted_scope.split(","))
    missing = required - granted
    if missing:
        raise RuntimeError(
            f"Missing required scope(s): {missing}. "
            "On the Strava auth page, make sure all requested scopes are checked."
        )

    return code


def _exchange_code(client_id: str, client_secret: str, auth_code: str) -> tuple[str, str]:
    print("Exchanging authorization code for tokens...")
    with httpx.Client(timeout=30) as client:
        resp = client.post(
            TOKEN_URL,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": auth_code,
                "grant_type": "authorization_code",
            },
        )
        if resp.status_code != 200:
            raise RuntimeError(
                f"Token exchange failed ({resp.status_code}): {resp.text}"
            )
        data = resp.json()
        athlete = data.get("athlete", {})
        print(
            f"  Authenticated as: {athlete.get('firstname', '?')} "
            f"{athlete.get('lastname', '?')} (id={athlete.get('id')})"
        )
        return data["access_token"], data["refresh_token"]


def _update_env(access_token: str, refresh_token: str) -> None:
    env_vars = {
        "STRAVA_ACCESS_TOKEN": access_token,
        "STRAVA_REFRESH_TOKEN": refresh_token,
    }

    existing_lines: list[str] = []
    if ENV_PATH.exists():
        existing_lines = ENV_PATH.read_text().splitlines()

    updated_keys: set[str] = set()
    new_lines: list[str] = []
    for line in existing_lines:
        key = line.split("=", 1)[0].strip() if "=" in line else ""
        if key in env_vars:
            new_lines.append(f"{key}={env_vars[key]}")
            updated_keys.add(key)
        else:
            new_lines.append(line)

    for key, value in env_vars.items():
        if key not in updated_keys:
            new_lines.append(f"{key}={value}")

    content = "\n".join(new_lines)
    if not content.endswith("\n"):
        content += "\n"

    ENV_PATH.write_text(content)
    print(f"  Credentials written to {ENV_PATH}")


def main() -> None:
    load_dotenv(ENV_PATH)

    client_id = os.getenv("STRAVA_CLIENT_ID")
    client_secret = os.getenv("STRAVA_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise SystemExit(
            "STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET must be in .env. "
            "Create an API app at https://www.strava.com/settings/api first."
        )

    print("=" * 60)
    print("Strava OAuth Setup (headless-friendly)")
    print("=" * 60)
    print()

    state = secrets.token_urlsafe(32)
    auth_url = _build_authorization_url(client_id, state)

    print("Open this URL in any browser and authorize the app:")
    print()
    print(f"  {auth_url}")
    print()
    print("After you click Authorize, Strava will redirect to a localhost")
    print("URL that won't load. That's fine — copy the FULL URL from your")
    print("browser's address bar and paste it below.")
    print()

    callback_url = input("Paste the redirect URL here: ").strip()
    auth_code = _extract_code_from_url(callback_url, state)

    access_token, refresh_token = _exchange_code(client_id, client_secret, auth_code)
    _update_env(access_token, refresh_token)

    print()
    print("=" * 60)
    print("Done! Restart Claude Code to load the Strava MCP server.")
    print("=" * 60)


if __name__ == "__main__":
    main()
