#!/usr/bin/env bash
set -euo pipefail
cd /root/.openclaw/workspace/projects/lucy-dashboard/frontend
exec python3 -m http.server 3000 --bind 127.0.0.1
