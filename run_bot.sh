#!/usr/bin/env bash
set -euo pipefail

# absolute project dir (adjust if you move it)
PROJ="/root/twitter-bot"
cd "$PROJ"

# Prevent overlapping runs
exec 9>run.lock
flock -n 9 || {
  echo "$(date -Is) Bot already running" >>logs/run.log
  exit 0
}

# Load environment variables (KEY=VALUE only)
set -a
. "$PROJ/.env"
set +a

# Activate Python virtual environment
. "$PROJ/.venv/bin/activate"

# Run bot
mkdir -p "$PROJ/logs"
echo "$(date -Is) starting bot" >>"$PROJ/logs/run.log"
python "$PROJ/bot.py" >>"$PROJ/logs/bot.log" 2>&1
echo "$(date -Is) finished bot (exit $?)" >>"$PROJ/logs/run.log"
