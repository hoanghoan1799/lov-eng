import { Html } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";
import { useRef } from "react";

import { NAME_TAG_HEIGHT } from "@/features/game/constants/game";
import { liveState } from "@/features/game/hooks/use-game-store";

export interface NameTagProps {
  playerId?: string;
  name: string;
  /** Small marker above the name, e.g. a quest icon for NPCs. */
  badge?: string;
}

export const NameTag = ({ playerId, name, badge }: NameTagProps) => {
  const bubbleRef = useRef<HTMLDivElement>(null);

  useFrame(() => {
    const element = bubbleRef.current;

    if (!element || !playerId) {
      return;
    }

    const bubble = liveState.bubbles.get(playerId);
    const isVisible = bubble !== undefined && bubble.until > Date.now();

    element.style.display = isVisible ? "block" : "none";

    if (isVisible && element.textContent !== bubble.text) {
      element.textContent = bubble.text;
    }
  });

  return (
    <Html position={[0, NAME_TAG_HEIGHT, 0]} center distanceFactor={14} zIndexRange={[20, 0]} style={{ pointerEvents: "none" }}>
      <div className="name-tag">
        <div ref={bubbleRef} className="chat-bubble" style={{ display: "none" }} />
        {badge ? <div className="name-badge">{badge}</div> : null}
        <div className="name-label">{name}</div>
      </div>
    </Html>
  );
};
