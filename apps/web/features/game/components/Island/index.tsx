import { useGLTF } from "@react-three/drei";
import { useLayoutEffect } from "react";
import type { Material, Mesh } from "three";

import { MODEL_URLS } from "@/features/game/constants/game";

const TRANSPARENT_RENDER_ORDER = 2;

export interface IslandProps {
  isLite: boolean;
}

export const Island = ({ isLite }: IslandProps) => {
  const { scene } = useGLTF(isLite ? MODEL_URLS.islandLite : MODEL_URLS.island);

  useLayoutEffect(() => {
    scene.traverse((child) => {
      const mesh = child as Mesh;

      if (!mesh.isMesh) {
        return;
      }

      const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];

      materials.forEach((material: Material) => {
        if (material.transparent) {
          // Glass must not write depth, or windows hide whatever is drawn after them.
          material.depthWrite = false;
          mesh.renderOrder = TRANSPARENT_RENDER_ORDER;
        }
      });
    });
  }, [scene]);

  return <primitive object={scene} />;
};
