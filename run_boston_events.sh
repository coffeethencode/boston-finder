#!/bin/bash
# Wrapper for daily cron — loads env vars and runs the event finder
# Output goes to ~/boston_events.log

source ~/.zshrc 2>/dev/null || true

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_BIN="/Users/brian/python-projects/myenv/bin/python3"

if [ ! -x "$PYTHON_BIN" ]; then
  PYTHON_BIN="$(command -v python3)"
fi

cd "$SCRIPT_DIR"

if [ "$#" -eq 0 ]; then
  export BOSTON_FINDER_DISABLE_OPEN=1
  exec "$PYTHON_BIN" "$SCRIPT_DIR/boston_events.py" --persona all
fi

exec "$PYTHON_BIN" "$SCRIPT_DIR/boston_events.py" "$@"
