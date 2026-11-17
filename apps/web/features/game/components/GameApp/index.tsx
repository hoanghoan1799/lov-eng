import { GameCanvas } from "@/features/game/components/GameCanvas";
import { Hud } from "@/features/game/components/Hud";
import { JoinScreen } from "@/features/game/components/JoinScreen";
import { useGameStore } from "@/features/game/hooks/use-game-store";

export const GameApp = () => {
  const status = useGameStore((state) => state.status);

  if (status !== "connected") {
    return <JoinScreen />;
  }

  return (
    <div className="game-root">
      <GameCanvas />
      <Hud />
    </div>
  );
};
