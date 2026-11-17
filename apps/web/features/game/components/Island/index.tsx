import { useGLTF } from "@react-three/drei";

import { MODEL_URLS } from "@/features/game/constants/game";

export interface IslandProps {
  isLite: boolean;
}

export const Island = ({ isLite }: IslandProps) => {
  const { scene } = useGLTF(isLite ? MODEL_URLS.islandLite : MODEL_URLS.island);

  return <primitive object={scene} />;
};
