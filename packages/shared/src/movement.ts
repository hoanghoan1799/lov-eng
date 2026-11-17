import { PARK_RADIUS, PLAYER_SPEED } from "./constants";

export interface Vec2 {
  x: number;
  z: number;
}

/** Clamps an input vector to length 1 so diagonal movement is not faster. */
export const normalizeIntent = (intent: Vec2): Vec2 => {
  const length = Math.hypot(intent.x, intent.z);

  if (length <= 1e-6) {
    return { x: 0, z: 0 };
  }

  const scale = Math.min(1, length) / length;

  return { x: intent.x * scale, z: intent.z * scale };
};

/** One movement step. Shared by client prediction and the authoritative server. */
export const stepPosition = (position: Vec2, intent: Vec2, deltaSeconds: number): Vec2 => {
  const direction = normalizeIntent(intent);
  const x = position.x + direction.x * PLAYER_SPEED * deltaSeconds;
  const z = position.z + direction.z * PLAYER_SPEED * deltaSeconds;
  const radius = Math.hypot(x, z);

  if (radius > PARK_RADIUS) {
    return { x: (x * PARK_RADIUS) / radius, z: (z * PARK_RADIUS) / radius };
  }

  return { x, z };
};
