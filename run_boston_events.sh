#!/bin/bash
# Wrapper for daily cron — loads env vars and runs the event finder
# Output goes to ~/boston_events.log

source ~/.zshrc 2>/dev/null || true

cd /Users/brian/python-projects
/Users/brian/python-projects/myenv/bin/python3 /Users/brian/python-projects/boston_events.py
