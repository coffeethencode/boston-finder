#!/bin/bash
# Wrapper for weekly cron — runs the oyster deals refresh.
# Output goes to ~/oyster_deals.log.

source ~/.zshrc 2>/dev/null || true

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_BIN="/Users/brian/python-projects/myenv/bin/python3"

if [ ! -x "$PYTHON_BIN" ]; then
  PYTHON_BIN="$(command -v python3)"
fi

cd "$SCRIPT_DIR"
exec "$PYTHON_BIN" "$SCRIPT_DIR/oyster_deals.py" "$@"
