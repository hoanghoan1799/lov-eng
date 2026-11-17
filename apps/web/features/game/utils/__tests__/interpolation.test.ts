import { describe, expect, it } from "vitest";

import { calculateSmoothing, lerpAngle } from "../interpolation";

describe("interpolation", () => {
  it("takes the short way round an angle", () => {
    const result = lerpAngle(3, -3, 0.5);

    expect(Math.abs(Math.cos(result) - Math.cos(Math.PI))).toBeLessThan(0.1);
  });

  it("smoothing grows with time and stays under one", () => {
    expect(calculateSmoothing(10, 0.016)).toBeLessThan(calculateSmoothing(10, 0.1));
    expect(calculateSmoothing(10, 0.5)).toBeLessThan(1);
  });
});
