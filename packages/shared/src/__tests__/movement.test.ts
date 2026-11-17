import { describe, expect, it } from "vitest";

import { PARK_RADIUS, PLAYER_SPEED } from "../constants";
import { normalizeIntent, stepPosition } from "../movement";

describe("normalizeIntent", () => {
  it("returns zero for no input", () => {
    expect(normalizeIntent({ x: 0, z: 0 })).toEqual({ x: 0, z: 0 });
  });

  it("limits a diagonal to length 1", () => {
    const result = normalizeIntent({ x: 1, z: 1 });

    expect(Math.hypot(result.x, result.z)).toBeCloseTo(1);
  });
});

describe("stepPosition", () => {
  it("moves at player speed", () => {
    const result = stepPosition({ x: 0, z: 0 }, { x: 1, z: 0 }, 1);

    expect(result.x).toBeCloseTo(PLAYER_SPEED);
    expect(result.z).toBeCloseTo(0);
  });

  it("does not move faster on a diagonal", () => {
    const result = stepPosition({ x: 0, z: 0 }, { x: 1, z: 1 }, 1);

    expect(Math.hypot(result.x, result.z)).toBeCloseTo(PLAYER_SPEED);
  });

  it("keeps the player inside the park", () => {
    const result = stepPosition({ x: PARK_RADIUS - 0.1, z: 0 }, { x: 1, z: 0 }, 10);

    expect(Math.hypot(result.x, result.z)).toBeLessThanOrEqual(PARK_RADIUS + 1e-9);
  });
});
