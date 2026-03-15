#!/usr/bin/env bash
set -euo pipefail
cd /root/.openclaw/workspace/projects/lucy-dashboard/backend
if [ ! -d .venv ]; then
  python3 -m venv .venv
  . .venv/bin/activate
  pip install -q -r requirements.txt
else
  . .venv/bin/activate
fi
exec uvicorn app.main:app --host 127.0.0.1 --port 8000
