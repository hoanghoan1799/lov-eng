import { PATH } from "@park/content";
import { useEffect } from "react";

import { ChatBox } from "@/features/game/components/ChatBox";
import { EmoteBar } from "@/features/game/components/EmoteBar";
import { Minimap } from "@/features/game/components/Minimap";
import { MissionDialog } from "@/features/game/components/MissionDialog";
import { PlayersPanel } from "@/features/game/components/PlayersPanel";
import { useGameStore } from "@/features/game/hooks/use-game-store";
import { useInteraction } from "@/features/game/hooks/use-interaction";

const NOTICE_MS = 4000;

export const Hud = () => {
  const nearest = useInteraction();
  const progressState = useGameStore((state) => state.progressState);
  const notice = useGameStore((state) => state.notice);
  const setNotice = useGameStore((state) => state.setNotice);

  useEffect(() => {
    if (!notice) {
      return undefined;
    }

    const timer = window.setTimeout(() => setNotice(null), NOTICE_MS);

    return () => window.clearTimeout(timer);
  }, [notice, setNotice]);

  return (
    <div className="hud">
      <div className="hud-top-left">
        <div className="xp">XP {progressState?.progress.xp ?? 0}</div>
        <ol className="path-list">
          {PATH.destinations.map((destination) => {
            const isUnlocked = progressState?.unlockedIds.includes(destination.id) ?? false;
            const isDone = destination.missions.length > 0 && destination.missions.every((id) => progressState?.progress.completedMissionIds.includes(id));

            return (
              <li key={destination.id} className={isUnlocked ? "open" : "locked"}>
                {isDone ? "✅" : isUnlocked ? "🟢" : "🔒"} {destination.name.en}
              </li>
            );
          })}
        </ol>
      </div>
      <div className="hud-top-right">
        <Minimap />
        <PlayersPanel />
      </div>
      {nearest ? <div className="interact-prompt">Press E to talk to {nearest.name}</div> : null}
      {notice ? <div className="notice">{notice}</div> : null}
      <div className="hud-help">WASD / arrows to move · Shift to run · drag to turn the camera · Enter to chat</div>
      <EmoteBar />
      <ChatBox />
      <MissionDialog />
    </div>
  );
};
