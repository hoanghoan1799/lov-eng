import { groundHeight, PLAYER_SPEED, RUN_SPEED, stepPlayer, TICK_HZ } from "@park/shared";
import { useFrame, useThree } from "@react-three/fiber";
import { useEffect, useRef } from "react";
import type { Group } from "three";

import { Avatar, type AvatarMotion } from "@/features/game/components/Avatar";
import { NameTag } from "@/features/game/components/NameTag";
import { CAMERA, RECONCILE_DISTANCE, RECONCILE_RATE } from "@/features/game/constants/game";
import { WORLD } from "@/features/game/constants/world";
import { liveState, useGameStore } from "@/features/game/hooks/use-game-store";
import { isEditingText, useKeyboardInput } from "@/features/game/hooks/use-keyboard-input";
import { sendMove } from "@/features/game/services/connection";
import type { Profile } from "@/features/game/types/game";
import { calculateWorldIntent } from "@/features/game/utils/input";
import { calculateSmoothing, lerpAngle } from "@/features/game/utils/interpolation";

export interface LocalPlayerProps {
  profile: Profile;
  selfId: string;
}

const SEND_INTERVAL = 1 / TICK_HZ;

export const LocalPlayer = ({ profile, selfId }: LocalPlayerProps) => {
  const groupRef = useRef<Group>(null);
  const motionRef = useRef<AvatarMotion>({ speed: 0, emote: null });
  const cameraRef = useRef<{ yaw: number; pitch: number }>({ yaw: 0, pitch: CAMERA.defaultPitch });
  const sendTimerRef = useRef(0);
  const sequenceRef = useRef(0);
  const wasMovingRef = useRef(false);
  const keysRef = useKeyboardInput();
  const { gl, camera } = useThree();

  useEffect(() => {
    const element = gl.domElement;
    let isDragging = false;

    const handleDown = () => {
      isDragging = true;
    };
    const handleUp = () => {
      isDragging = false;
    };
    const handleMove = (event: PointerEvent) => {
      if (!isDragging) {
        return;
      }

      cameraRef.current.yaw -= event.movementX * CAMERA.dragSpeed;
      cameraRef.current.pitch = Math.min(CAMERA.maxPitch, Math.max(CAMERA.minPitch, cameraRef.current.pitch + event.movementY * CAMERA.dragSpeed));
    };

    element.addEventListener("pointerdown", handleDown);
    window.addEventListener("pointerup", handleUp);
    window.addEventListener("pointermove", handleMove);

    return () => {
      element.removeEventListener("pointerdown", handleDown);
      window.removeEventListener("pointerup", handleUp);
      window.removeEventListener("pointermove", handleMove);
    };
  }, [gl]);

  useFrame((_state, rawDelta) => {
    const group = groupRef.current;
    const self = liveState.self;

    if (!group || !self.hasSpawned) {
      return;
    }

    const delta = Math.min(rawDelta, 0.1);
    const isBlocked = isEditingText() || useGameStore.getState().isMissionOpen;
    const keys = keysRef.current;
    const intent = isBlocked ? { x: 0, z: 0 } : calculateWorldIntent(keys, cameraRef.current.yaw);
    const isMoving = intent.x !== 0 || intent.z !== 0;
    const isRunning = keys.run && isMoving;
    const next = stepPlayer({ x: self.x, z: self.z }, intent, delta, WORLD, isRunning);
    const server = liveState.players.get(selfId);

    self.x = next.x;
    self.z = next.z;

    if (server && Math.hypot(server.x - self.x, server.z - self.z) > RECONCILE_DISTANCE) {
      const pull = calculateSmoothing(RECONCILE_RATE, delta);

      self.x += (server.x - self.x) * pull;
      self.z += (server.z - self.z) * pull;
    }

    if (isMoving) {
      self.ry = lerpAngle(self.ry, Math.atan2(intent.x, intent.z), calculateSmoothing(14, delta));
    }

    const y = groundHeight(WORLD, self.x, self.z);

    group.position.set(self.x, y, self.z);
    group.rotation.y = self.ry;

    const emote = liveState.emotes.get(selfId);

    motionRef.current.speed = isMoving ? (isRunning ? RUN_SPEED : PLAYER_SPEED) : 0;
    motionRef.current.emote = emote && emote.until > Date.now() ? capitalize(emote.emote) : null;

    sendTimerRef.current += delta;

    if (sendTimerRef.current >= SEND_INTERVAL && (isMoving || wasMovingRef.current)) {
      sendTimerRef.current = 0;
      sequenceRef.current += 1;
      sendMove(intent.x, intent.z, isRunning, sequenceRef.current);
    }

    wasMovingRef.current = isMoving;

    const { yaw, pitch } = cameraRef.current;
    const flat = Math.cos(pitch) * CAMERA.distance;
    const follow = calculateSmoothing(CAMERA.smoothing, delta);

    camera.position.x += (self.x + Math.sin(yaw) * flat - camera.position.x) * follow;
    camera.position.y += (y + CAMERA.lookHeight + Math.sin(pitch) * CAMERA.distance - camera.position.y) * follow;
    camera.position.z += (self.z + Math.cos(yaw) * flat - camera.position.z) * follow;
    camera.lookAt(self.x, y + CAMERA.lookHeight, self.z);
  });

  return (
    <group ref={groupRef}>
      <Avatar look={profile.look} motionRef={motionRef} />
      <NameTag playerId={selfId} name={profile.name} />
    </group>
  );
};

const capitalize = (value: string): string => `${value.charAt(0).toUpperCase()}${value.slice(1)}`;
