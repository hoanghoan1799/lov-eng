import { GameCanvas } from "@/features/game/components/GameCanvas";
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
    </div>
  );
};
