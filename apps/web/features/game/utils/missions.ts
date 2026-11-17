import { PATH } from "@park/content";
import { NPC_INTERACT_RANGE, TYPED_FALLBACK_AFTER_ATTEMPTS } from "@park/shared";

export interface NpcSpot {
  destinationId: string;
  name: string;
  x: number;
  z: number;
  facingX: number;
  facingZ: number;
}

/** The mission an NPC offers: the first one not completed yet, else the first (replay). */
export const pickMissionId = (destinationId: string, completedIds: readonly string[]): string | null => {
  const destination = PATH.destinations.find((item) => item.id === destinationId);
  const next = destination?.missions.find((id) => !completedIds.includes(id));

  return next ?? destination?.missions[0] ?? null;
};

export const findNearestNpc = (npcs: readonly NpcSpot[], x: number, z: number): NpcSpot | null => {
  let best: NpcSpot | null = null;
  let bestDistance = NPC_INTERACT_RANGE;

  npcs.forEach((npc) => {
    const distance = Math.hypot(npc.x - x, npc.z - z);

    if (distance <= bestDistance) {
      best = npc;
      bestDistance = distance;
    }
  });

  return best;
};

/** Typing replaces speaking after repeated failures or when the microphone does not work. */
export const canTypeAnswer = (attempts: number, isMicUnavailable: boolean): boolean =>
  isMicUnavailable || attempts >= TYPED_FALLBACK_AFTER_ATTEMPTS;
