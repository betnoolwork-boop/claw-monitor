# Backend

Suggested stack:
- FastAPI

## First implementation targets
- `GET /api/registry/summary`
- `GET /api/registry/agents`
- `GET /api/registry/topology`
- `GET /api/growth/summary`
- `GET /api/growth/proposals`
- `GET /api/growth/report`

## Canonical inputs
- `../../config/agent-registry.json`
- `../claw-evolution-backlog.json`
- `../claw-growth-report.md`

## Local run
```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
