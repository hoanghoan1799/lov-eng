# Game server image (Fly.io, Railway, Render, any container host with WebSocket support).
FROM node:22-slim
RUN corepack enable
WORKDIR /app
COPY . .
RUN pnpm install --frozen-lockfile && pnpm --filter @park/game-server build
ENV NODE_ENV=production PORT=2567 PROGRESS_FILE=/data/progress.json REPORT_LOG=/data/reports.jsonl
EXPOSE 2567
CMD ["node", "apps/game-server/dist/index.js"]
