import { JoinScreenView } from "@/features/game/components/JoinScreenView";
import { useGameStore } from "@/features/game/hooks/use-game-store";
import { useJoinForm } from "@/features/game/hooks/use-join-form";

export const JoinScreen = () => {
  const form = useJoinForm();
  const status = useGameStore((state) => state.status);
  const errorMessage = useGameStore((state) => state.errorMessage);

  return <JoinScreenView {...form} isConnecting={status === "connecting"} errorMessage={errorMessage} />;
};
