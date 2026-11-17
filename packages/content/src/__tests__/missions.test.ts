import { evaluateTurn } from "@park/shared";
import { describe, expect, it } from "vitest";

import { MISSIONS, PATH } from "../index";

describe("mission content", () => {
  it("gives every destination at least one registered mission", () => {
    PATH.destinations.forEach((destination) => {
      expect(destination.missions.length, destination.id).toBeGreaterThan(0);
      destination.missions.forEach((id) => expect(MISSIONS[id]?.destinationId, id).toBe(destination.id));
    });
  });

  it("accepts every listed answer for its own turn", () => {
    Object.values(MISSIONS).forEach((mission) => {
      mission.turns.forEach((turn) => {
        turn.accepted.forEach((answer) => {
          expect(evaluateTurn(turn, answer, mission.cefr).isPassed, `${mission.id}/${turn.id}: ${answer}`).toBe(true);
        });
      });
    });
  });

  it("rejects unrelated speech", () => {
    Object.values(MISSIONS).forEach((mission) => {
      mission.turns.forEach((turn) => {
        expect(evaluateTurn(turn, "banana pizza", mission.cefr).isPassed, `${mission.id}/${turn.id}`).toBe(false);
      });
    });
  });
});
