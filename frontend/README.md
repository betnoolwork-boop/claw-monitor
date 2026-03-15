# Frontend

Current MVP:
- static HTML/CSS/JS shell
- reads backend API from the current site origin (`/api/*` via reverse proxy)
- screens: Overview, Agents, System, Task Queue, Growth, Topology, Control Chat
- live-ish auto-refresh every 15s with manual refresh button
- improved card styling, status color badges, and mobile-friendly layout

## Local run
```bash
cd frontend
python3 -m http.server 3000
```

## Future upgrade path
- Next.js
- React
- TypeScript
- Tailwind CSS
- shadcn/ui

## First UI targets
- Overview page
- Agents page
- Topology page
- Growth block
- Chat panel
