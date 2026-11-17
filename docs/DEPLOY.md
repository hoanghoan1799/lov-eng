# Deploying

The web client is static-friendly and runs on Vercel. The game server keeps WebSocket connections open, so it
cannot run on Vercel's serverless functions. Host it on a container platform (Fly.io, Railway, Render, ...).

## 1. Game server

Build and run the image from the repo root:

```bash
docker build -t park-game-server .
docker run -p 2567:2567 -v park-data:/data park-game-server
```

On the platform, expose port 2567 over HTTPS/WSS and mount a volume at `/data` (progress and report logs).
Environment: `PORT` (default 2567), `PROGRESS_FILE`, `REPORT_LOG`.

## 2. Web client (Vercel)

Set the server address and redeploy (the value is baked in at build time):

```
NEXT_PUBLIC_GAME_SERVER_URL=wss://your-game-server.example.com
```

Vercel project settings: root directory `apps/web`, install command `pnpm install --frozen-lockfile` at the repo
root (enable "include files outside the root directory").

Without the variable the client falls back to `ws://localhost:2567`, which only works when you run both locally.
