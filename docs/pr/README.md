# Pull request plan

Stacked branches (each is based on the previous one). Merge in order, or merge the last one to get everything.

1. `chore/monorepo-shared-content` – pnpm/Turborepo, lint config, CI, `@park/shared`, `@park/content`
2. `feat/blender-tools` – Blender scripts and design docs
3. `feat/game-server` – Colyseus server with a two-client smoke test
4. `feat/web-island-multiplayer` – Next.js app: island, avatars, movement, multiplayer, join screen
5. `feat/web-missions-chat` – HUD, NPC missions with speech and typed fallback, chat, emotes, reports, minimap
