import { describe, expect, it } from "vitest";

import { type PathFile, pathFileSchema } from "../path";
import { getUnlockedDestinationIds, isDestinationComplete } from "../progress";

const PATH: PathFile = pathFileSchema.parse({
  version: 1,
  destinations: [
    {
      id: "park",
      order: 1,
      name: { vi: "Công viên", en: "Park" },
      cefr: "A1",
      scene: "park",
      isHub: true,
      phase: "mvp",
      situations: ["greetings"],
      missions: ["park-greeting"],
    },
    {
      id: "cafe",
      order: 2,
      name: { vi: "Quán cà phê", en: "Cafe" },
      cefr: "A1",
      scene: "cafe",
      phase: "mvp",
      situations: ["ordering"],
      missions: ["cafe-order"],
    },
    {
      id: "restaurant",
      order: 3,
      name: { vi: "Nhà hàng", en: "Restaurant" },
      cefr: "A2",
      scene: "restaurant",
      phase: "mvp",
      situations: ["booking"],
      missions: [],
    },
  ],
});

describe("getUnlockedDestinationIds", () => {
  it("opens only the hub for a new learner", () => {
    expect(getUnlockedDestinationIds(PATH, [])).toEqual(["park"]);
  });

  it("opens the next destination when the previous one is complete", () => {
    expect(getUnlockedDestinationIds(PATH, ["park-greeting"])).toEqual(["park", "cafe"]);
  });

  it("opens a destination after a completed one, even if it has no missions yet", () => {
    expect(getUnlockedDestinationIds(PATH, ["park-greeting", "cafe-order"])).toEqual(["park", "cafe", "restaurant"]);
  });

  it("opens a destination the learner skipped to", () => {
    expect(getUnlockedDestinationIds(PATH, [], ["restaurant"])).toEqual(["park", "restaurant"]);
  });
});

describe("isDestinationComplete", () => {
  it("never counts a destination without missions as complete", () => {
    const restaurant = PATH.destinations[2];

    expect(restaurant && isDestinationComplete(restaurant, ["park-greeting", "cafe-order"])).toBe(false);
  });

  it("requires every mission", () => {
    const [park] = PATH.destinations;

    expect(park && isDestinationComplete(park, ["park-greeting"])).toBe(true);
    expect(park && isDestinationComplete(park, [])).toBe(false);
  });
});

describe("pathFileSchema", () => {
  it("rejects a path whose first destination is not the hub", () => {
    const result = pathFileSchema.safeParse({
      version: 1,
      destinations: [
        {
          id: "cafe",
          order: 1,
          name: { vi: "Quán cà phê", en: "Cafe" },
          cefr: "A1",
          scene: "cafe",
          phase: "mvp",
          situations: ["ordering"],
          missions: [],
        },
      ],
    });

    expect(result.success).toBe(false);
  });
});
