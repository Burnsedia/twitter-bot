#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

# Prevent overlapping runs
exec 9>run.lock
flock -n 9 || {
  echo "Another run in progress"
  exit 0
}

# Export env from .env safely
set -a
. ./.env
set +a

# Activate venv
. .venv/bin/activate

# Run your script and log output
mkdir -p logs
python bot.py >>logs/bot.log 2>&1
