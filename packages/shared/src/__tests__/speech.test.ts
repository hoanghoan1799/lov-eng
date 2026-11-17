import { describe, expect, it } from "vitest";

import {
  calculateUtteranceScore,
  matchUtterance,
  normalizeUtterance,
  PASS_THRESHOLD_BY_CEFR,
} from "../speech";

const ACCEPTED = ["I would like a coffee, please", "Can I have a coffee, please"];

describe("normalizeUtterance", () => {
  it("lowercases, strips punctuation and expands contractions", () => {
    expect(normalizeUtterance("I'm fine, thank you!")).toEqual(["i", "am", "fine", "thank", "you"]);
  });

  it("treats a curly apostrophe like a straight one", () => {
    expect(normalizeUtterance("I’d like tea")).toEqual(["i", "would", "like", "tea"]);
  });
});

describe("calculateUtteranceScore", () => {
  it("is 1 for the same sentence ignoring case and punctuation", () => {
    expect(calculateUtteranceScore("i would like a COFFEE please", ACCEPTED[0] ?? "")).toBe(1);
  });

  it("gives partial credit to a near miss", () => {
    const score = calculateUtteranceScore("i would like a cofee please", ACCEPTED[0] ?? "");

    expect(score).toBeGreaterThan(0.9);
    expect(score).toBeLessThan(1);
  });
});

describe("matchUtterance", () => {
  it("passes an accepted sentence and reports the best match", () => {
    const result = matchUtterance("can i have a coffee please", ACCEPTED, PASS_THRESHOLD_BY_CEFR.A1);

    expect(result.isPassed).toBe(true);
    expect(result.bestMatch).toBe("Can I have a coffee, please");
  });

  it("fails an unrelated sentence", () => {
    const result = matchUtterance("where is the station", ACCEPTED, PASS_THRESHOLD_BY_CEFR.A1);

    expect(result.isPassed).toBe(false);
  });

  it("is stricter at higher levels", () => {
    const heard = "i would like coffee please";
    const a1 = matchUtterance(heard, ACCEPTED, PASS_THRESHOLD_BY_CEFR.A1);
    const b2 = matchUtterance(heard, ACCEPTED, PASS_THRESHOLD_BY_CEFR.B2);

    expect(a1.isPassed).toBe(true);
    expect(b2.isPassed).toBe(false);
  });
});
