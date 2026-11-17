import { describe, expect, it } from "vitest";

import { calculateWorldIntent, type KeyState } from "../input";

const KEYS: KeyState = { up: false, down: false, left: false, right: false, run: false };

describe("calculateWorldIntent", () => {
  it("is zero with no keys", () => {
    expect(calculateWorldIntent(KEYS, 1)).toEqual({ x: 0, z: 0 });
  });

  it("walks north (-Z) with the default camera", () => {
    const intent = calculateWorldIntent({ ...KEYS, up: true }, 0);

    expect(intent.x).toBeCloseTo(0);
    expect(intent.z).toBeCloseTo(-1);
  });

  it("strafes east with D", () => {
    const intent = calculateWorldIntent({ ...KEYS, right: true }, 0);

    expect(intent.x).toBeCloseTo(1);
    expect(intent.z).toBeCloseTo(0);
  });

  it("turns with the camera yaw and normalizes diagonals", () => {
    const intent = calculateWorldIntent({ ...KEYS, up: true, right: true }, Math.PI / 2);

    expect(Math.hypot(intent.x, intent.z)).toBeCloseTo(1);
    expect(intent.x).toBeLessThan(0);
  });
});
