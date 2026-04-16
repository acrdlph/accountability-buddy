#!/usr/bin/env bash
# Launcher for the chrisdoc/hevy-mcp server.
# - Loads HEVY_API_KEY from the project's .env
# - Uses Node 24 (hevy-mcp requires >=24.0.0) without changing the system default
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

# Load env vars from .env
set -a
# shellcheck disable=SC1091
source "$PROJECT_DIR/.env"
set +a

# Prefer Node 24 if installed via nvm, otherwise fall back to whatever's on PATH.
NODE24_DIR="$HOME/.nvm/versions/node/v24.15.0/bin"
if [ -d "$NODE24_DIR" ]; then
  export PATH="$NODE24_DIR:$PATH"
fi

exec npx -y hevy-mcp
