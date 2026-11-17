import { WORLD_COLLIDERS, WORLD_HEIGHTMAP, WORLD_LAYOUT } from "@park/content";
import type { World } from "@park/shared";

export const WORLD: World = {
  boxes: WORLD_COLLIDERS.boxes,
  obbs: WORLD_COLLIDERS.obbs,
  circles: WORLD_COLLIDERS.circles,
  heightmap: WORLD_HEIGHTMAP,
  walkables: WORLD_LAYOUT.walkables,
  walkRadius: WORLD_LAYOUT.walkRadius,
};

export const SPAWN = WORLD_LAYOUT.spawn;
export const ISLAND_RADIUS = WORLD_LAYOUT.radius;
