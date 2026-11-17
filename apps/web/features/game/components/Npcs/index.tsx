import { groundHeight } from "@park/shared";
import { useMemo, useRef } from "react";

import { Avatar, type AvatarMotion } from "@/features/game/components/Avatar";
import { NameTag } from "@/features/game/components/NameTag";
import { NPC_HAIRS, NPC_SKIN_TOPS } from "@/features/game/constants/game";
import { NPCS } from "@/features/game/constants/npcs";
import { WORLD } from "@/features/game/constants/world";
import { useGameStore } from "@/features/game/hooks/use-game-store";
import { type NpcSpot,pickMissionId } from "@/features/game/utils/missions";

interface NpcProps {
  npc: NpcSpot;
  index: number;
}

const QUEST_BADGE = "❗";

const Npc = ({ npc, index }: NpcProps) => {
  const motionRef = useRef<AvatarMotion>({ speed: 0, emote: null });
  const progressState = useGameStore((state) => state.progressState);
  const look = useMemo(
    () => ({
      gender: index % 2 === 0 ? ("girl" as const) : ("boy" as const),
      top: NPC_SKIN_TOPS[index % NPC_SKIN_TOPS.length] ?? "#e67e22",
      hair: NPC_HAIRS[index % NPC_HAIRS.length] ?? "#111111",
    }),
    [index],
  );
  const isUnlocked = progressState?.unlockedIds.includes(npc.destinationId) ?? false;
  const missionId = pickMissionId(npc.destinationId, progressState?.progress.completedMissionIds ?? []);
  const isDone = missionId !== null && (progressState?.progress.completedMissionIds.includes(missionId) ?? false);
  const badge = isUnlocked && missionId && !isDone ? QUEST_BADGE : undefined;
  const y = groundHeight(WORLD, npc.x, npc.z);

  return (
    <group position={[npc.x, y, npc.z]} rotation={[0, Math.atan2(npc.facingX, npc.facingZ), 0]}>
      <Avatar look={look} motionRef={motionRef} />
      <NameTag name={npc.name} badge={badge} />
    </group>
  );
};

export const Npcs = () => (
  <>
    {NPCS.map((npc, index) => (
      <Npc key={npc.destinationId} npc={npc} index={index} />
    ))}
  </>
);
