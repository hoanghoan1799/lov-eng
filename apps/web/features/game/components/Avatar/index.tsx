import type { AvatarLook } from "@park/shared";
import { useAnimations, useGLTF } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";
import { type MutableRefObject, useEffect, useMemo, useRef } from "react";
import { CanvasTexture, type Group, type Material, type Mesh, NearestFilter, SRGBColorSpace, type Texture } from "three";
import { clone } from "three/examples/jsm/utils/SkeletonUtils.js";

import { ANIMATION, MODEL_URLS, PALETTE_CELLS, RUN_SPEED_THRESHOLD, WALK_SPEED_THRESHOLD } from "@/features/game/constants/game";
import { paintCells, shadeHex } from "@/features/game/utils/avatar-palette";

export interface AvatarMotion {
  speed: number;
  /** Animation clip name of an active emote, e.g. "Wave". */
  emote: string | null;
}

export interface AvatarProps {
  look: AvatarLook;
  motionRef: MutableRefObject<AvatarMotion>;
}

const PALETTE_WIDTH = 256;
const PALETTE_HEIGHT = 8;

const createRecoloredTexture = (source: Texture, look: AvatarLook): Texture | null => {
  const canvas = document.createElement("canvas");
  const context = canvas.getContext("2d");

  if (!context) {
    return null;
  }

  canvas.width = PALETTE_WIDTH;
  canvas.height = PALETTE_HEIGHT;
  context.drawImage(source.image as CanvasImageSource, 0, 0);
  paintCells(context, [
    { cell: PALETTE_CELLS.hair, hex: look.hair },
    { cell: PALETTE_CELLS.brow, hex: shadeHex(look.hair, 0.8) },
    { cell: PALETTE_CELLS.top, hex: look.top },
    { cell: PALETTE_CELLS.topShade, hex: shadeHex(look.top, 0.75) },
  ]);

  const texture = new CanvasTexture(canvas);

  texture.flipY = false;
  texture.colorSpace = SRGBColorSpace;
  texture.magFilter = NearestFilter;
  texture.minFilter = NearestFilter;
  texture.generateMipmaps = false;

  return texture;
};

const pickClip = (motion: AvatarMotion): string => {
  if (motion.emote) {
    return motion.emote;
  }

  if (motion.speed > RUN_SPEED_THRESHOLD) {
    return ANIMATION.run;
  }

  return motion.speed > WALK_SPEED_THRESHOLD ? ANIMATION.walk : ANIMATION.idle;
};

export const Avatar = ({ look, motionRef }: AvatarProps) => {
  const url = look.gender === "girl" ? MODEL_URLS.girl : MODEL_URLS.boy;
  const { scene, animations } = useGLTF(url);
  const groupRef = useRef<Group>(null);
  const currentClipRef = useRef<string>("");
  const model = useMemo(() => clone(scene), [scene]);
  const { actions } = useAnimations(animations, groupRef);

  useEffect(() => {
    const created: Texture[] = [];

    model.traverse((child) => {
      const mesh = child as Mesh;

      if (!mesh.isMesh) {
        return;
      }

      const material = (mesh.material as Material).clone() as Material & { map: Texture | null };

      if (material.map) {
        const texture = createRecoloredTexture(material.map, look);

        if (texture) {
          material.map = texture;
          created.push(texture);
        }
      }

      mesh.material = material;
    });

    return () => created.forEach((texture) => texture.dispose());
  }, [model, look]);

  useFrame(() => {
    const clipName = pickClip(motionRef.current);

    if (clipName === currentClipRef.current) {
      return;
    }

    const next = actions[clipName] ?? actions[ANIMATION.idle];

    if (!next) {
      return;
    }

    actions[currentClipRef.current]?.fadeOut(ANIMATION.fade);
    next.reset().fadeIn(ANIMATION.fade).play();
    currentClipRef.current = clipName;
  });

  return (
    <group ref={groupRef}>
      <primitive object={model} />
    </group>
  );
};
