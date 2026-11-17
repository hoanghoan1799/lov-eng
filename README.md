# Park English

A 3D multiplayer island where adults (18+) practise English by walking around, chatting with people nearby and
talking to NPCs. Ten destinations unlock in order (park → coffee shop → restaurant → … → airport); the park is the
social hub.

## Layout

| Path | What it is |
| --- | --- |
| `apps/web` | Next.js 16 + React Three Fiber client (island, avatars, chat, mission dialog) |
| `apps/game-server` | Colyseus 0.18 room: authoritative movement and collisions, chat, reports, missions, progress |
| `packages/shared` | zod protocol, movement/collision/height maths, speech matcher, progress rules (server and client share it) |
| `packages/content` | `path.json`, mission JSON, and the island data exported from Blender (colliders, heightmap, layout) |
| `tools/blender` | Headless Blender scripts that build the characters and the island and export the GLBs |
| `docs` | Product spec, prototype, island review page, notes |

## Run it

```bash
pnpm install
pnpm --filter @park/game-server dev   # ws://localhost:2567
pnpm --filter @park/web dev           # http://localhost:3000
```

Open the web app in two browser windows to see multiplayer. Add `?lite=1` to force the lighter island model
(used automatically on phones). Set `NEXT_PUBLIC_GAME_SERVER_URL` to point the client at another server.

Checks: `pnpm lint && pnpm typecheck && pnpm test && pnpm build`.

## Controls

WASD / arrows move, Shift runs, drag to turn the camera, Enter chats (people within 25 m hear you), `E` talks to an
NPC, the emote bar plays animations, the players list lets you report someone.

## Rebuilding the models

```bash
/Applications/Blender.app/Contents/MacOS/Blender --background --python tools/blender/build_world.py -- assets/world --export
```

The `.blend` files and preview renders are git-ignored. The runtime GLBs live in `apps/web/public/models`, and the
data JSON in `packages/content/world`.

## Not built yet

Voice chat (LiveKit), Google sign-in, face expressions and outfit variants, and real server-side speech scoring.
Speech uses the browser's `SpeechRecognition` with a typed fallback; see the review page for the full list.
