# Habitify MCP for Claude Code

Connects Claude Code to [Habitify](https://habitify.me) via MCP with automatic OAuth token refresh.

## How it works

`habitify_proxy.py` is a stdio MCP server that sits between Claude Code and Habitify's MCP server (`https://mcp.habitify.me/mcp`). It:

- Automatically refreshes OAuth access tokens using a stored refresh token
- Discovers all Habitify tools and re-exposes them to Claude Code
- Opens a fresh SSE connection per tool call (Habitify drops idle connections after ~30s)
- Retries with a fresh token on auth errors

## Setup

### 1. Install dependencies

```bash
cd /home/claudeuser/code/habit-tracking
python3 -m venv .venv
.venv/bin/pip install "mcp[cli]>=1.27" httpx python-dotenv
```

### 2. Run OAuth setup

```bash
.venv/bin/python habitify_oauth_setup.py
```

This will:
1. Register an OAuth client with Habitify automatically
2. Print an authorization URL -- open it in **any** browser (doesn't need to be on the same machine)
3. Log in to Habitify and authorize the app
4. You'll be redirected to a `localhost:8976/callback?code=...` URL that won't load -- this is expected
5. Copy the **full URL** from your browser's address bar and paste it back into the terminal
6. The script exchanges the code for tokens and saves `HABITIFY_CLIENT_ID` and `HABITIFY_REFRESH_TOKEN` to `.env`

### 3. Restart Claude Code

Start Claude Code from the `habit-tracking` directory (or any directory with `.mcp.json` pointing here). The Habitify tools will be available automatically.

## Files

| File | Purpose |
|---|---|
| `habitify_proxy.py` | MCP proxy server (stdio) with auto token refresh |
| `habitify_oauth_setup.py` | One-time OAuth PKCE setup script |
| `.mcp.json` | Claude Code MCP server configuration |
| `.env` | Stores `HABITIFY_CLIENT_ID`, `HABITIFY_REFRESH_TOKEN` (gitignored) |

## Re-authentication

If the refresh token expires or stops working, re-run the OAuth setup:

```bash
.venv/bin/python habitify_oauth_setup.py
```

This registers a fresh client and token pair. No need to change any other config.
