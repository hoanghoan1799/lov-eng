import { PATH } from "@park/content";
import { PLAYER_RADIUS, resolveCollisions } from "@park/shared";
import { describe, expect, it } from "vitest";

import { DESTINATION_IDS, NPC_POSITIONS, SPAWN, WORLD } from "../world";

const isFree = (x: number, z: number): boolean => {
  const resolved = resolveCollisions({ x, z }, WORLD, PLAYER_RADIUS * 0.5);

  return Math.hypot(resolved.x - x, resolved.z - z) < 0.01;
};

describe("island world on the server", () => {
  it("spawns the player on free ground", () => {
    expect(isFree(SPAWN.x, SPAWN.z)).toBe(true);
  });

  it("has an NPC on free ground for every destination", () => {
    expect(DESTINATION_IDS).toEqual(PATH.destinations.map((destination) => destination.id));

    DESTINATION_IDS.forEach((id) => {
      const npc = NPC_POSITIONS[id];

      expect(npc, id).toBeDefined();
      expect(isFree(npc?.x ?? 0, npc?.z ?? 0), id).toBe(true);
    });
  });

  it("lets the player walk from the spawn to every NPC", () => {
    const step = 0.5;
    const origin = -60;
    const size = 240;
    const key = (i: number, j: number) => i * size + j;
    const toIndex = (value: number) => Math.round((value - origin) / step);
    const seen = new Set<number>([key(toIndex(SPAWN.x), toIndex(SPAWN.z))]);
    const queue: [number, number][] = [[toIndex(SPAWN.x), toIndex(SPAWN.z)]];

    while (queue.length > 0) {
      const [i, j] = queue.shift() ?? [0, 0];

      [[1, 0], [-1, 0], [0, 1], [0, -1]].forEach(([di, dj]) => {
        const a = i + (di ?? 0);
        const b = j + (dj ?? 0);
        const x = origin + a * step;
        const z = origin + b * step;

        if (a >= 0 && b >= 0 && a < size && b < size && Math.hypot(x, z) <= WORLD.walkRadius && !seen.has(key(a, b)) && isFree(x, z)) {
          seen.add(key(a, b));
          queue.push([a, b]);
        }
      });
    }

    DESTINATION_IDS.forEach((id) => {
      const npc = NPC_POSITIONS[id];

      expect(seen.has(key(toIndex(npc?.x ?? 0), toIndex(npc?.z ?? 0))), id).toBe(true);
    });
  });
});
