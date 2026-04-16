#!/usr/bin/env bash
# Launcher for the r-huijts/strava-mcp server.
# - Loads Strava credentials from the project's .env
# - Uses the system Node (>=18 required; Node 22 default is fine)
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

set -a
# shellcheck disable=SC1091
source "$PROJECT_DIR/.env"
set +a

exec npx -y @r-huijts/strava-mcp-server
