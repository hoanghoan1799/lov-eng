import { groundHeight, RUN_SPEED } from "@park/shared";
import { useFrame } from "@react-three/fiber";
import { useRef } from "react";
import type { Group } from "three";

import { Avatar, type AvatarMotion } from "@/features/game/components/Avatar";
import { NameTag } from "@/features/game/components/NameTag";
import { INTERPOLATION_RATE } from "@/features/game/constants/game";
import { WORLD } from "@/features/game/constants/world";
import { liveState, useGameStore } from "@/features/game/hooks/use-game-store";
import { calculateSmoothing, lerpAngle } from "@/features/game/utils/interpolation";

interface RemoteAvatarProps {
  playerId: string;
}

const capitalize = (value: string): string => `${value.charAt(0).toUpperCase()}${value.slice(1)}`;

const RemoteAvatar = ({ playerId }: RemoteAvatarProps) => {
  const groupRef = useRef<Group>(null);
  const motionRef = useRef<AvatarMotion>({ speed: 0, emote: null });
  const hasPlacedRef = useRef(false);
  const player = liveState.players.get(playerId);

  useFrame((_state, delta) => {
    const group = groupRef.current;
    const target = liveState.players.get(playerId);

    if (!group || !target) {
      return;
    }

    if (!hasPlacedRef.current) {
      group.position.set(target.x, 0, target.z);
      group.rotation.y = target.ry;
      hasPlacedRef.current = true;
    }

    const follow = calculateSmoothing(INTERPOLATION_RATE, Math.min(delta, 0.1));

    group.position.x += (target.x - group.position.x) * follow;
    group.position.z += (target.z - group.position.z) * follow;
    group.position.y = groundHeight(WORLD, group.position.x, group.position.z);
    group.rotation.y = lerpAngle(group.rotation.y, target.ry, follow);

    const emote = liveState.emotes.get(playerId);

    motionRef.current.speed = Math.min(RUN_SPEED, target.speed);
    motionRef.current.emote = emote && emote.until > Date.now() ? capitalize(emote.emote) : null;
  });

  if (!player) {
    return null;
  }

  return (
    <group ref={groupRef}>
      <Avatar look={player.look} motionRef={motionRef} />
      <NameTag playerId={playerId} name={player.name} />
    </group>
  );
};

export const RemotePlayers = () => {
  const playerIds = useGameStore((state) => state.playerIds);
  const selfId = useGameStore((state) => state.selfId);

  return (
    <>
      {playerIds
        .filter((id) => id !== selfId)
        .map((id) => (
          <RemoteAvatar key={id} playerId={id} />
        ))}
    </>
  );
};
