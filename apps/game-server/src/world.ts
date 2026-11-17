import { PATH, WORLD_COLLIDERS, WORLD_HEIGHTMAP, WORLD_LAYOUT } from "@park/content";
import type { Vec2, World } from "@park/shared";

export const WORLD: World = {
  boxes: WORLD_COLLIDERS.boxes,
  obbs: WORLD_COLLIDERS.obbs,
  circles: WORLD_COLLIDERS.circles,
  heightmap: WORLD_HEIGHTMAP,
  walkables: WORLD_LAYOUT.walkables,
  walkRadius: WORLD_LAYOUT.walkRadius,
};

export const SPAWN: Vec2 = { x: WORLD_LAYOUT.spawn.x, z: WORLD_LAYOUT.spawn.z };

/** Where each destination's NPC stands, keyed by destination id. */
export const NPC_POSITIONS: Record<string, Vec2> = Object.fromEntries([
  [WORLD_LAYOUT.park.id, { x: WORLD_LAYOUT.park.npcX, z: WORLD_LAYOUT.park.npcZ }],
  ...WORLD_LAYOUT.places.map((place) => [place.id, { x: place.npcX, z: place.npcZ }]),
]);

export const DESTINATION_IDS = PATH.destinations.map((destination) => destination.id);
