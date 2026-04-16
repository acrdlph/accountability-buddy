# Accountability Buddy

An easily extendible personal accountability system that plugs into health, fitness and habit trackers.

Current integrations:
- [Habitify](https://habitify.me) — habit tracking (via custom MCP proxy with OAuth refresh)
- [Hevy](https://hevyapp.com) — workout tracking (via [chrisdoc/hevy-mcp](https://github.com/chrisdoc/hevy-mcp))
- [Telegram](https://telegram.org) — primary interface, including voice notes transcribed with OpenAI Whisper

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

### Hevy MCP launcher

`hevy_launcher.sh` is a thin wrapper that loads the Hevy API key from `.env` and runs [chrisdoc/hevy-mcp](https://github.com/chrisdoc/hevy-mcp) via `npx`. The hevy-mcp package requires Node 24+, so the launcher prepends a Node 24 install (via nvm) to `PATH` without changing the system default. Requires a Hevy PRO subscription for API access.

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

Add these to `.env`:

```
OPENAI_API_KEY=sk-...     # for voice note transcription
HEVY_API_KEY=<uuid>       # get at https://hevy.com/settings?developer (requires Hevy PRO)
```

### 3b. Install Node 24 (for Hevy MCP)

The Hevy MCP server requires Node 24+. Install it via nvm:

```bash
nvm install 24
nvm alias default 22   # keep system default unchanged if you prefer
```

The launcher (`hevy_launcher.sh`) picks up Node 24 automatically if it's installed at `~/.nvm/versions/node/v24.15.0/`.

### 4. Register the MCP servers in `~/.mcp.json`

Claude Code looks for MCP server definitions in `~/.mcp.json` (in your home directory — **not in this repo**, since it's user-level config and references absolute paths specific to your machine).

Create or edit `~/.mcp.json`:

```json
{
  "mcpServers": {
    "habitify": {
      "type": "stdio",
      "command": "/ABSOLUTE/PATH/TO/habit-tracking/.venv/bin/python",
      "args": ["/ABSOLUTE/PATH/TO/habit-tracking/habitify_proxy.py"]
    },
    "hevy": {
      "type": "stdio",
      "command": "/ABSOLUTE/PATH/TO/habit-tracking/hevy_launcher.sh"
    }
  }
}
```

Replace `/ABSOLUTE/PATH/TO/habit-tracking` with the actual path where you cloned this repo. If you don't use Hevy, omit its entry.

### 5. Start Claude Code

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
| `habitify_proxy.py` | Habitify MCP proxy (stdio) with auto token refresh |
| `habitify_oauth_setup.py` | One-time Habitify OAuth PKCE setup script |
| `hevy_launcher.sh` | Wrapper that loads `.env` and runs `hevy-mcp` on Node 24 |
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

- **Strava** -- running and cycling
