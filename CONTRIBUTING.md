# Contributing

Thanks for your interest in improving Accountability Buddy. Contributions of new integrations, bug fixes, and docs are all welcome.

## Development setup

Follow the [README](README.md) setup steps to get a working local instance: clone the repo, create the `.venv`, install Python deps, and register the MCP servers you want in `~/.mcp.json`. For local development you only need the integration(s) you're actually touching.

## Project layout

- **`CLAUDE.md`** — generic assistant behavior, shared by everyone. Changes here affect all users, so keep it free of personal specifics.
- **`CLAUDE.local.md`** (gitignored) — your personal config. Never commit this.
- **`*_proxy.py` / `*_launcher.sh`** — the MCP server entry points.
- **`*_oauth_setup.py`** — one-time OAuth helpers for services that need it.

## Adding a new integration

Each integration is an MCP server registered in `~/.mcp.json`. To add one:

1. Provide the server, either by wrapping an existing community MCP server in a launcher script (see `hevy_launcher.sh` / `strava_launcher.sh`) or by writing a small stdio proxy (see `habitify_proxy.py` for the pattern, including OAuth refresh).
2. If the service needs OAuth, add a one-time setup script following `habitify_oauth_setup.py` / `strava_oauth_setup.py`.
3. Read any secrets from environment variables loaded from `.env`. Add the new variables to `.env.example` (with placeholder values only).
4. Add the server block to `.mcp.json.example`.
5. Document the integration's behavior rules in `CLAUDE.md` (generic) and the setup steps in the README.

## Secrets and personal data

**Never commit secrets or personal data.** `.env`, `.mcp.json`, `CLAUDE.local.md`, and `nutrition/` are all gitignored for this reason. Before opening a PR, run:

```bash
git status
git diff --staged
```

and confirm none of those files appear. Only `.example` files (with placeholder values) should ever be committed.

## Pull requests and issues

- Keep PRs focused on a single change.
- Describe what the change does and why in the PR body.
- For new integrations, note which MCP server you used and any subscription/API requirements.
- Open an issue first if you want to discuss a larger change before building it.
