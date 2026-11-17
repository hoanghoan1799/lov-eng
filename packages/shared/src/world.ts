import { PLAYER_SPEED, RUN_SPEED } from "./constants";
import { normalizeIntent, type Vec2 } from "./movement";

/** Axis-aligned box: x0, z0, x1, z1, top height, source object name. */
export type Box = readonly [number, number, number, number, number, string];
/** Oriented box: centre x, z, axis u (ux, uz; v = (-uz, ux)), half sizes along u and v, top height, name. */
export type Obb = readonly [number, number, number, number, number, number, number, string];
/** Circle: x, z, radius. */
export type Circle = readonly [number, number, number];

export interface Heightmap {
  size: number;
  step: number;
  origin: number;
  heights: readonly (readonly number[])[];
}

/** An oriented rectangle that raises the ground (bridge decks). */
export interface Walkable {
  x: number;
  z: number;
  hw: number;
  hl: number;
  dx: number;
  dz: number;
  top: number;
}

export interface World {
  boxes: readonly Box[];
  obbs: readonly Obb[];
  circles: readonly Circle[];
  heightmap: Heightmap;
  walkables: readonly Walkable[];
  walkRadius: number;
}

export const PLAYER_RADIUS = 0.45;

/** Pushes a position out of every collider it overlaps. */
export const resolveCollisions = (position: Vec2, world: Pick<World, "boxes" | "obbs" | "circles">, radius = PLAYER_RADIUS): Vec2 => {
  let x = position.x;
  let z = position.z;

  for (const [cx, cz, r] of world.circles) {
    const dx = x - cx;
    const dz = z - cz;
    const min = r + radius;
    const distanceSquared = dx * dx + dz * dz;

    if (distanceSquared < min * min) {
      const distance = Math.sqrt(distanceSquared);

      if (distance > 1e-6) {
        x = cx + (dx / distance) * min;
        z = cz + (dz / distance) * min;
      } else {
        x = cx + min;
      }
    }
  }

  for (const [x0, z0, x1, z1] of world.boxes) {
    if (x > x0 - radius && x < x1 + radius && z > z0 - radius && z < z1 + radius) {
      const left = x - (x0 - radius);
      const right = x1 + radius - x;
      const top = z - (z0 - radius);
      const bottom = z1 + radius - z;
      const smallest = Math.min(left, right, top, bottom);

      if (smallest === left) {
        x = x0 - radius;
      } else if (smallest === right) {
        x = x1 + radius;
      } else if (smallest === top) {
        z = z0 - radius;
      } else {
        z = z1 + radius;
      }
    }
  }

  for (const [cx, cz, ux, uz, hu, hv] of world.obbs) {
    const du = (x - cx) * ux + (z - cz) * uz;
    const dv = -(x - cx) * uz + (z - cz) * ux;

    if (Math.abs(du) < hu + radius && Math.abs(dv) < hv + radius) {
      const overU = hu + radius - Math.abs(du);
      const overV = hv + radius - Math.abs(dv);
      let pu = du;
      let pv = dv;

      if (overU < overV) {
        pu = Math.sign(du || 1) * (hu + radius);
      } else {
        pv = Math.sign(dv || 1) * (hv + radius);
      }

      x = cx + pu * ux - pv * uz;
      z = cz + pu * uz + pv * ux;
    }
  }

  return { x, z };
};

/** Bilinear terrain height from the exported grid. */
export const sampleTerrainHeight = (heightmap: Heightmap, x: number, z: number): number => {
  const { size, step, origin, heights } = heightmap;
  const gx = Math.min(size - 1.001, Math.max(0, (x - origin) / step));
  const gz = Math.min(size - 1.001, Math.max(0, (z - origin) / step));
  const ix = Math.floor(gx);
  const iz = Math.floor(gz);
  const fx = gx - ix;
  const fz = gz - iz;
  const row0 = heights[iz] ?? [];
  const row1 = heights[iz + 1] ?? row0;
  const h00 = row0[ix] ?? 0;
  const h10 = row0[ix + 1] ?? h00;
  const h01 = row1[ix] ?? h00;
  const h11 = row1[ix + 1] ?? h10;

  return h00 * (1 - fx) * (1 - fz) + h10 * fx * (1 - fz) + h01 * (1 - fx) * fz + h11 * fx * fz;
};

/** Ground height at a point: the terrain, raised by a bridge deck when the point is on one. */
export const groundHeight = (world: Pick<World, "heightmap" | "walkables">, x: number, z: number): number => {
  let height = sampleTerrainHeight(world.heightmap, x, z);

  for (const w of world.walkables) {
    const along = (x - w.x) * w.dx + (z - w.z) * w.dz;
    const across = (x - w.x) * -w.dz + (z - w.z) * w.dx;

    if (Math.abs(along) <= w.hl && Math.abs(across) <= w.hw) {
      height = Math.max(height, w.top);
    }
  }

  return height;
};

const MAX_SUBSTEP_METRES = 0.25;

/** One authoritative movement step on the island: speed, rim clamp, colliders. Sub-steps so a long step cannot tunnel through a wall. */
export const stepPlayer = (position: Vec2, intent: Vec2, deltaSeconds: number, world: World, isRunning = false): Vec2 => {
  const direction = normalizeIntent(intent);
  const speed = isRunning ? RUN_SPEED : PLAYER_SPEED;
  const distance = speed * deltaSeconds * Math.hypot(direction.x, direction.z);
  const steps = Math.max(1, Math.ceil(distance / MAX_SUBSTEP_METRES));
  let current = position;

  for (let i = 0; i < steps; i += 1) {
    let x = current.x + (direction.x * speed * deltaSeconds) / steps;
    let z = current.z + (direction.z * speed * deltaSeconds) / steps;
    const radius = Math.hypot(x, z);

    if (radius > world.walkRadius) {
      x = (x * world.walkRadius) / radius;
      z = (z * world.walkRadius) / radius;
    }

    current = resolveCollisions({ x, z }, world);
  }

  return current;
};

const CIRCLE_BLOCK_HEIGHT = 3.5;
const CAMERA_MARGIN = 0.35;

export interface Vec3 {
  x: number;
  y: number;
  z: number;
}

/**
 * How far along the line from `from` (the player's head) to `to` (the wanted camera spot) the camera can go
 * before it would sit inside a building, a tree trunk or the ground. Returns a fraction between `minimum` and 1.
 */
export const calculateCameraClearance = (world: World, from: Vec3, to: Vec3, minimum = 0.25, steps = 24): number => {
  for (let i = 1; i <= steps; i += 1) {
    const t = i / steps;
    const x = from.x + (to.x - from.x) * t;
    const y = from.y + (to.y - from.y) * t;
    const z = from.z + (to.z - from.z) * t;
    const isBlocked =
      y < groundHeight(world, x, z) + CAMERA_MARGIN ||
      world.boxes.some(([x0, z0, x1, z1, top]) => x > x0 && x < x1 && z > z0 && z < z1 && y < top + CAMERA_MARGIN) ||
      world.circles.some(([cx, cz, r]) => Math.hypot(x - cx, z - cz) < r + CAMERA_MARGIN && y < CIRCLE_BLOCK_HEIGHT) ||
      world.obbs.some(([cx, cz, ux, uz, hu, hv, top]) => {
        const du = (x - cx) * ux + (z - cz) * uz;
        const dv = -(x - cx) * uz + (z - cz) * ux;

        return Math.abs(du) < hu && Math.abs(dv) < hv && y < top + CAMERA_MARGIN;
      });

    if (isBlocked) {
      return Math.max(minimum, (i - 1) / steps);
    }
  }

  return 1;
};
