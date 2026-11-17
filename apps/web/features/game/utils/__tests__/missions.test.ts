import { describe, expect, it } from "vitest";

import { canTypeAnswer, findNearestNpc, type NpcSpot,pickMissionId } from "../missions";

const NPCS: NpcSpot[] = [
  { destinationId: "park", name: "Sam", x: 0, z: 15, facingX: 0, facingZ: -1 },
  { destinationId: "coffee", name: "Mia", x: -32, z: -6, facingX: -1, facingZ: 0 },
];

describe("missions utils", () => {
  it("offers the first unfinished mission, else a replay", () => {
    expect(pickMissionId("park", [])).toBe("park-greeting");
    expect(pickMissionId("park", ["park-greeting"])).toBe("park-greeting");
    expect(pickMissionId("nowhere", [])).toBeNull();
  });

  it("finds an NPC only within range", () => {
    expect(findNearestNpc(NPCS, 1, 13)?.name).toBe("Sam");
    expect(findNearestNpc(NPCS, 30, 30)).toBeNull();
  });

  it("allows typing after repeated failures or without a mic", () => {
    expect(canTypeAnswer(0, false)).toBe(false);
    expect(canTypeAnswer(5, false)).toBe(true);
    expect(canTypeAnswer(0, true)).toBe(true);
  });
});
