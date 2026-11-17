import { describe, expect, it } from "vitest";

import { isAdult } from "../age";
import { cleanChatText, filterChatText } from "../chat";
import { calculateMissionStars, calculateTurnStars } from "../mission";
import { applyMissionResult, createEmptyProgress } from "../progress";

describe("calculateTurnStars", () => {
  it("gives 3 stars for a first-try spoken pass", () => {
    expect(calculateTurnStars(1, "voice")).toBe(3);
  });

  it("gives 2 stars for a later spoken pass", () => {
    expect(calculateTurnStars(3, "voice")).toBe(2);
  });

  it("gives 1 star for typing", () => {
    expect(calculateTurnStars(1, "typed")).toBe(1);
  });
});

describe("calculateMissionStars", () => {
  it("rounds the average and never goes below 1", () => {
    expect(calculateMissionStars([3, 3, 2])).toBe(3);
    expect(calculateMissionStars([1, 1, 2])).toBe(1);
    expect(calculateMissionStars([])).toBe(1);
  });
});

describe("applyMissionResult", () => {
  it("pays XP only on the first completion and keeps the best stars", () => {
    const first = applyMissionResult(createEmptyProgress(), "m1", 2, 20);
    const replay = applyMissionResult(first, "m1", 3, 20);

    expect(first.xp).toBe(20);
    expect(replay.xp).toBe(20);
    expect(replay.stars.m1).toBe(3);
    expect(replay.completedMissionIds).toEqual(["m1"]);
  });
});

describe("isAdult", () => {
  const NOW = new Date("2026-06-01T00:00:00Z");

  it("accepts 18 and older, rejects younger", () => {
    expect(isAdult(2008, NOW)).toBe(true);
    expect(isAdult(2009, NOW)).toBe(false);
  });
});

describe("chat helpers", () => {
  it("masks blocked words but not words that merely contain them", () => {
    expect(filterChatText("what the shit")).toBe("what the ****");
    expect(filterChatText("classic")).toBe("classic");
  });

  it("collapses whitespace", () => {
    expect(cleanChatText("  hi    there \n")).toBe("hi there");
  });
});
