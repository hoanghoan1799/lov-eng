import { PATH } from "@park/content";
import { useCallback, useEffect, useState } from "react";

import { NPCS } from "@/features/game/constants/npcs";
import { liveState, useGameStore } from "@/features/game/hooks/use-game-store";
import { isEditingText } from "@/features/game/hooks/use-keyboard-input";
import { sendMissionStart } from "@/features/game/services/connection";
import { findNearestNpc, type NpcSpot,pickMissionId } from "@/features/game/utils/missions";

const POLL_MS = 200;

/** Finds the NPC in talking range and starts its mission when the player presses E. */
export const useInteraction = (): { nearest: NpcSpot | null; onTalk: () => void } => {
  const [nearest, setNearest] = useState<NpcSpot | null>(null);

  useEffect(() => {
    const timer = window.setInterval(() => {
      const next = findNearestNpc(NPCS, liveState.self.x, liveState.self.z);

      setNearest((current) => (current?.destinationId === next?.destinationId ? current : next));
    }, POLL_MS);

    return () => window.clearInterval(timer);
  }, []);

  const handleTalk = useCallback(() => {
    const store = useGameStore.getState();

    if (store.isMissionOpen || !nearest) {
      return;
    }

    const progress = store.progressState;
    const missionId = pickMissionId(nearest.destinationId, progress?.progress.completedMissionIds ?? []);
    const destination = PATH.destinations.find((item) => item.id === nearest.destinationId);

    if (!missionId) {
      store.setNotice(`${nearest.name} has no mission yet. Coming soon!`);

      return;
    }

    if (!progress?.unlockedIds.includes(nearest.destinationId)) {
      store.setNotice(`${destination?.name.en ?? "This place"} is locked. Finish the previous place first.`);

      return;
    }

    sendMissionStart(missionId);
  }, [nearest]);

  useEffect(() => {
    const handleKey = (event: KeyboardEvent) => {
      if (event.code === "KeyE" && !isEditingText()) {
        handleTalk();
      }
    };

    window.addEventListener("keydown", handleKey);

    return () => window.removeEventListener("keydown", handleKey);
  }, [handleTalk]);

  return { nearest, onTalk: handleTalk };
};
