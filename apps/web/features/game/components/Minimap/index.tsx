import { useEffect, useRef } from "react";

import { NPCS } from "@/features/game/constants/npcs";
import { ISLAND_RADIUS } from "@/features/game/constants/world";
import { liveState, useGameStore } from "@/features/game/hooks/use-game-store";

const SIZE = 150;

export const Minimap = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const scale = SIZE / 2 / ISLAND_RADIUS;
    const toMap = (value: number) => SIZE / 2 + value * scale;
    const timer = window.setInterval(() => {
      const context = canvasRef.current?.getContext("2d");
      const selfId = useGameStore.getState().selfId;

      if (!context) {
        return;
      }

      context.clearRect(0, 0, SIZE, SIZE);
      context.fillStyle = "rgba(120, 200, 120, 0.85)";
      context.beginPath();
      context.arc(SIZE / 2, SIZE / 2, SIZE / 2 - 2, 0, Math.PI * 2);
      context.fill();
      context.fillStyle = "#e67e22";
      NPCS.forEach((npc) => context.fillRect(toMap(npc.x) - 2, toMap(npc.z) - 2, 4, 4));
      liveState.players.forEach((player, id) => {
        context.fillStyle = id === selfId ? "#ffffff" : "#2e86de";
        context.beginPath();
        context.arc(toMap(id === selfId ? liveState.self.x : player.x), toMap(id === selfId ? liveState.self.z : player.z), 3, 0, Math.PI * 2);
        context.fill();
      });
    }, 150);

    return () => window.clearInterval(timer);
  }, []);

  return <canvas ref={canvasRef} className="minimap" width={SIZE} height={SIZE} aria-label="Map" />;
};
