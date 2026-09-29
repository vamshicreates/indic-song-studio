#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

# Use existing workspace venv if available, otherwise create local .venv
if [ -x "$DIR/../MiniMax-H3/.venv/bin/python" ]; then
  PY="$DIR/../MiniMax-H3/.venv/bin/python"
elif [ -x "$DIR/.venv/bin/python" ]; then
  PY="$DIR/.venv/bin/python"
else
  python3 -m venv .venv
  .venv/bin/pip install -q -r requirements.txt
  PY="$DIR/.venv/bin/python"
fi

PORT="${PORT:-7865}"
echo "🚀 Starting Indic Song Studio at http://127.0.0.1:${PORT}"
exec "$PY" server.py
