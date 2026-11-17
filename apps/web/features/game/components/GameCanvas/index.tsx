import { Canvas } from "@react-three/fiber";
import { Suspense } from "react";

import { Island } from "@/features/game/components/Island";
import { LocalPlayer } from "@/features/game/components/LocalPlayer";
import { Npcs } from "@/features/game/components/Npcs";
import { RemotePlayers } from "@/features/game/components/RemotePlayers";
import { useGameStore } from "@/features/game/hooks/use-game-store";
import { useIsLiteQuality } from "@/features/game/hooks/use-quality";

const SKY_COLOR = "#bfe3ff";
const MAX_PIXEL_RATIO = 1.75;

export const GameCanvas = () => {
  const isLite = useIsLiteQuality();
  const profile = useGameStore((state) => state.profile);
  const selfId = useGameStore((state) => state.selfId);

  return (
    <Canvas camera={{ fov: 55, near: 0.1, far: 400, position: [0, 8, 12] }} dpr={[1, MAX_PIXEL_RATIO]} gl={{ antialias: !isLite }}>
      <color attach="background" args={[SKY_COLOR]} />
      <fog attach="fog" args={[SKY_COLOR, 90, 220]} />
      <hemisphereLight args={["#ffffff", "#9fb8a0", 1.2]} />
      <directionalLight position={[40, 60, 20]} intensity={1.6} />
      <Suspense fallback={null}>
        <Island isLite={isLite} />
        <Npcs />
        <RemotePlayers />
        {profile && selfId ? <LocalPlayer profile={profile} selfId={selfId} /> : null}
      </Suspense>
    </Canvas>
  );
};
