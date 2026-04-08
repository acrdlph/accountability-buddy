# Accountability Buddy

An easily extendible personal accountability system that plugs into health, fitness and habit trackers.

Currently integrates with [Habitify](https://habitify.me) via MCP, with Telegram as the primary interface (including voice note support via OpenAI Whisper).

## Architecture

The system runs as a long-lived **Claude Code instance** with the [Telegram channels plugin](https://github.com/anthropics/claude-plugins-official), acting as an always-on assistant you interact with via Telegram (text and voice notes).

Ideal deployment: a remote server (or any always-on machine) running Claude Code inside a **tmux** session so it persists across SSH disconnects.

```
You (Telegram) <-> Claude Code + Telegram plugin <-> MCP servers (Habitify, etc.)
```

### Habitify MCP proxy

`habitify_proxy.py` is a stdio MCP server that sits between Claude Code and Habitify's MCP server (`https://mcp.habitify.me/mcp`). It:

- Automatically refreshes OAuth access tokens using a stored refresh token
- Discovers all Habitify tools and re-exposes them to Claude Code
- Opens a fresh SSE connection per tool call (Habitify drops idle connections after ~30s)
- Retries with a fresh token on auth errors

## Setup

### 0. Prerequisites

- A remote server or always-on machine (Linux recommended)
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) installed and authenticated
- The [Telegram channels plugin](https://github.com/anthropics/claude-plugins-official) installed and paired with your Telegram bot
- tmux (to keep the session alive)

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

### 3. Add API keys

Add your OpenAI API key (for voice note transcription) to `.env`:

```
OPENAI_API_KEY=sk-...
```

### 4. Start Claude Code

Start a tmux session and launch Claude Code from the project directory:

```bash
tmux new -s buddy
cd /path/to/habit-tracking
claude
```

Detach with `Ctrl+B, D`. The session stays alive and keeps listening for Telegram messages.

## Files

| File | Purpose |
|---|---|
| `habitify_proxy.py` | MCP proxy server (stdio) with auto token refresh |
| `habitify_oauth_setup.py` | One-time OAuth PKCE setup script |
| `.mcp.json` | Claude Code MCP server configuration |
| `transcribe.py` | Voice note transcription via OpenAI Whisper API |
| `CLAUDE.md` | Assistant instructions for habit tracking and input parsing |
| `.env` | Stores API keys and tokens (gitignored) |

## Re-authentication

If the refresh token expires or stops working, re-run the OAuth setup:

```bash
.venv/bin/python habitify_oauth_setup.py
```

This registers a fresh client and token pair. No need to change any other config.

## Roadmap

Upcoming integrations:

- **Hevy** -- workout tracker
- **Strava** -- running and cycling
