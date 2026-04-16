# Accountability Buddy

An easily extendible personal accountability system that plugs into health, fitness and habit trackers.

**Current integrations:**
- [Habitify](https://habitify.me) — habit tracking (via custom MCP proxy with OAuth refresh)
- [Hevy](https://hevyapp.com) — workout tracking (via [chrisdoc/hevy-mcp](https://github.com/chrisdoc/hevy-mcp))
- [Strava](https://strava.com) — running & cycling, read-only (via [r-huijts/strava-mcp](https://github.com/r-huijts/strava-mcp))
- [Telegram](https://telegram.org) — primary interface, including voice notes transcribed with OpenAI Whisper

## Architecture

The system runs as a long-lived **Claude Code instance** with the [Telegram channels plugin](https://github.com/anthropics/claude-plugins-official), acting as an always-on assistant you interact with via Telegram (text and voice notes).

Ideal deployment: a remote server (or any always-on machine) running Claude Code inside a **tmux** session so it persists across SSH disconnects.

```
You (Telegram) <-> Claude Code + Telegram plugin <-> MCP servers (Habitify, Hevy, Strava)
```

## Setup

### 1. Prerequisites

- A Unix-like environment (Linux, macOS, or WSL on Windows) — the launcher scripts are bash, and the deployment assumes tmux. An always-on host (VPS, home server) is ideal so the assistant stays reachable.
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) installed and authenticated
- The [Telegram channels plugin](https://github.com/anthropics/claude-plugins-official) installed and paired with your Telegram bot
- tmux
- Python 3.9+
- Node.js 22+ (system default), plus nvm if you want Hevy (needs Node 24+)

### 2. Clone and install Python dependencies

```bash
git clone https://github.com/acrdlph/accountability-buddy.git habit-tracking
cd habit-tracking
python3 -m venv .venv
.venv/bin/pip install "mcp[cli]>=1.27" httpx python-dotenv openai
```

All credentials live in `.env` (gitignored). Copy `.env.example` as a starting template.

---

Integrations below are independent — set up only the ones you want.

### 3. Habitify (habit tracking)

Uses a custom MCP proxy that handles OAuth refresh automatically.

Run the one-time OAuth setup:

```bash
.venv/bin/python habitify_oauth_setup.py
```

It prints an auth URL; open it in any browser, authorize, then paste the redirect URL back into the terminal. The script saves `HABITIFY_CLIENT_ID` and `HABITIFY_REFRESH_TOKEN` to `.env`.

### 4. Hevy (workout tracking)

Requires a [Hevy PRO](https://hevy.com/pricing) subscription (~$3/mo) to access the API.

1. **Install Node 24** (hevy-mcp needs ≥24, but keep your system default untouched):
   ```bash
   nvm install 24
   nvm alias default 22
   ```
   `hevy_launcher.sh` picks up Node 24 automatically from `~/.nvm/versions/node/v24.15.0/`.

2. **Get an API key** at https://hevy.com/settings?developer

3. **Add to `.env`:**
   ```
   HEVY_API_KEY=<your-uuid>
   ```

### 5. Strava (running & cycling, read-only)

Strava is read-only — activities come from your watch/phone automatically, so the MCP server only *reads* them.

1. **Create a Strava API app** at https://www.strava.com/settings/api
   - Set **Authorization Callback Domain** to `localhost`
   - Upload any logo (required)

2. **Add the app credentials to `.env`:**
   ```
   STRAVA_CLIENT_ID=<number>
   STRAVA_CLIENT_SECRET=<hex>
   ```

3. **Run the one-time OAuth setup:**
   ```bash
   .venv/bin/python strava_oauth_setup.py
   ```
   Same flow as Habitify: open auth URL → authorize → paste redirect URL back. The script saves `STRAVA_ACCESS_TOKEN` and `STRAVA_REFRESH_TOKEN` to `.env`. The MCP server handles refresh automatically afterwards.

### 6. OpenAI (Whisper, for voice notes)

Add your API key to `.env`:

```
OPENAI_API_KEY=sk-...
```

This powers `transcribe.py`, which the assistant calls when a Telegram voice note arrives.

### 7. Register the MCP servers in `~/.mcp.json`

Claude Code looks for MCP server definitions in `~/.mcp.json` — in your home directory, **not in this repo**, since it's user-level config with machine-specific absolute paths.

Create or edit `~/.mcp.json` (omit any servers you don't use):

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
    },
    "strava": {
      "type": "stdio",
      "command": "/ABSOLUTE/PATH/TO/habit-tracking/strava_launcher.sh"
    }
  }
}
```

Replace `/ABSOLUTE/PATH/TO/habit-tracking` with your actual clone path.

### 8. Launch Claude Code

```bash
tmux new -s buddy
cd /path/to/habit-tracking
claude --dangerously-skip-permissions --channels plugin:telegram@claude-plugins-official
```

Detach with `Ctrl+B, D`. The session stays alive and keeps listening for Telegram messages.

**The `--channels` flag is required.** Without it, Claude Code doesn't route inbound Telegram notifications into the session — you'll still be able to *send* replies, but user messages never arrive. If Telegram messages stop appearing in your session, this flag is almost always the cause.

The `--dangerously-skip-permissions` flag lets the assistant act autonomously on tool calls. Drop it if you want interactive approval, but expect the experience to be awkward on a headless server.

## Files

| File | Purpose |
|---|---|
| `habitify_proxy.py` | Habitify MCP proxy (stdio) with auto OAuth refresh |
| `habitify_oauth_setup.py` | One-time Habitify OAuth PKCE setup |
| `hevy_launcher.sh` | Wrapper that loads `.env` and runs `hevy-mcp` on Node 24 |
| `strava_launcher.sh` | Wrapper that loads `.env` and runs `strava-mcp` via `npx` |
| `strava_oauth_setup.py` | One-time Strava OAuth flow (obtains access + refresh tokens) |
| `transcribe.py` | Voice note transcription via OpenAI Whisper |
| `CLAUDE.md` | Assistant behavior rules (input parsing, cross-service logic, response style) |
| `.env` | API keys and tokens (gitignored) |
| `.env.example` | Template of the env vars required by the integrations |

## Troubleshooting

- **Telegram messages aren't reaching the session** — almost always means you launched `claude` without `--channels plugin:telegram@claude-plugins-official`. Exit and relaunch with the flag.
- **Habitify auth failures** — the refresh token probably expired. Re-run `.venv/bin/python habitify_oauth_setup.py` to get a fresh one.
- **Strava auth failures** — re-run `.venv/bin/python strava_oauth_setup.py` (only needed if the refresh token itself was invalidated; access tokens refresh automatically).
- **`npx -y hevy-mcp` complains about Node version** — make sure Node 24 is installed via nvm (`nvm install 24`); the launcher picks it up from `~/.nvm/versions/node/v24.15.0/`.

## Roadmap

No active roadmap items — feel free to open issues or PRs for new integrations.
