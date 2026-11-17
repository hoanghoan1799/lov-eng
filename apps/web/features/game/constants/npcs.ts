import { WORLD_LAYOUT } from "@park/content";

import type { NpcSpot } from "@/features/game/utils/missions";

export const NPCS: NpcSpot[] = [
  {
    destinationId: WORLD_LAYOUT.park.id,
    name: WORLD_LAYOUT.park.npcName,
    x: WORLD_LAYOUT.park.npcX,
    z: WORLD_LAYOUT.park.npcZ,
    facingX: WORLD_LAYOUT.park.npcFacingX,
    facingZ: WORLD_LAYOUT.park.npcFacingZ,
  },
  ...WORLD_LAYOUT.places.map((place) => ({
    destinationId: place.id,
    name: place.npcName,
    x: place.npcX,
    z: place.npcZ,
    facingX: place.npcFacingX,
    facingZ: place.npcFacingZ,
  })),
];
