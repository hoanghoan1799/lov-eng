import { describe, expect, it } from "vitest";

import { PLAYER_SPEED } from "../constants";
import { groundHeight, PLAYER_RADIUS, resolveCollisions, sampleTerrainHeight, stepPlayer, type World } from "../world";

const FLAT = { size: 3, step: 10, origin: -10, heights: [[0, 0, 0], [0, 2, 0], [0, 0, 0]] };

const WORLD: World = {
  boxes: [[10, -2, 14, 2, 3, "COL_Wall"]],
  obbs: [[0, -20, 0.7071, 0.7071, 4, 1, 3, "COL_Diagonal"]],
  circles: [[-10, 0, 1]],
  heightmap: FLAT,
  walkables: [{ x: 0, z: 20, hw: 2, hl: 5, dx: 0, dz: 1, top: 0.5 }],
  walkRadius: 50,
};

describe("resolveCollisions", () => {
  it("pushes a point out of a circle", () => {
    const result = resolveCollisions({ x: -9.5, z: 0 }, WORLD);

    expect(Math.hypot(result.x + 10, result.z)).toBeGreaterThanOrEqual(1 + PLAYER_RADIUS - 1e-6);
  });

  it("pushes a point out of a box along the shortest side", () => {
    const result = resolveCollisions({ x: 9.8, z: 0 }, WORLD);

    expect(result.x).toBeCloseTo(10 - PLAYER_RADIUS);
    expect(result.z).toBe(0);
  });

  it("leaves a free point alone", () => {
    expect(resolveCollisions({ x: 0, z: 0 }, WORLD)).toEqual({ x: 0, z: 0 });
  });
});

describe("oriented boxes", () => {
  it("blocks inside the rotated footprint but not in the empty corner of its bounding box", () => {
    const inside = resolveCollisions({ x: 0, z: -20 }, WORLD);
    const corner = resolveCollisions({ x: 3.4, z: -23.4 }, WORLD);

    expect(Math.hypot(inside.x, inside.z + 20)).toBeGreaterThan(1);
    expect(corner).toEqual({ x: 3.4, z: -23.4 });
  });
});

describe("terrain height", () => {
  it("is bilinear between grid points", () => {
    expect(sampleTerrainHeight(FLAT, 0, 0)).toBeCloseTo(2);
    expect(sampleTerrainHeight(FLAT, 5, 0)).toBeCloseTo(1);
  });

  it("is raised by a bridge deck", () => {
    expect(groundHeight(WORLD, 0, 22)).toBe(0.5);
    expect(groundHeight(WORLD, 6, 22)).toBeLessThan(0.5);
  });
});

describe("stepPlayer", () => {
  it("moves at walking speed and stops at a wall", () => {
    const free = stepPlayer({ x: 0, z: 0 }, { x: 1, z: 0 }, 1, WORLD);
    const blocked = stepPlayer({ x: 8, z: 0 }, { x: 1, z: 0 }, 1, WORLD);

    expect(free.x).toBeCloseTo(PLAYER_SPEED);
    expect(blocked.x).toBeLessThanOrEqual(10 - PLAYER_RADIUS + 1e-6);
  });

  it("clamps to the island rim", () => {
    const result = stepPlayer({ x: 49, z: 0 }, { x: 1, z: 0 }, 5, { ...WORLD, boxes: [], circles: [] });

    expect(Math.hypot(result.x, result.z)).toBeLessThanOrEqual(50 + 1e-6);
  });
});
