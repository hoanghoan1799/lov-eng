export interface KeyState {
  up: boolean;
  down: boolean;
  left: boolean;
  right: boolean;
  run: boolean;
}

export interface WorldIntent {
  x: number;
  z: number;
}

/**
 * Turns keyboard state into a world-space direction relative to the camera yaw.
 * Yaw 0 means the camera sits south of the player looking north (-Z).
 */
export const calculateWorldIntent = (keys: KeyState, yaw: number): WorldIntent => {
  const forward = (keys.up ? 1 : 0) - (keys.down ? 1 : 0);
  const side = (keys.right ? 1 : 0) - (keys.left ? 1 : 0);

  if (forward === 0 && side === 0) {
    return { x: 0, z: 0 };
  }

  const sin = Math.sin(yaw);
  const cos = Math.cos(yaw);
  const x = side * cos - forward * sin;
  const z = side * -sin - forward * cos;
  const length = Math.hypot(x, z);

  return { x: x / length, z: z / length };
};

export const KEY_BINDINGS: Record<string, keyof KeyState> = {
  KeyW: "up",
  ArrowUp: "up",
  KeyS: "down",
  ArrowDown: "down",
  KeyA: "left",
  ArrowLeft: "left",
  KeyD: "right",
  ArrowRight: "right",
  ShiftLeft: "run",
  ShiftRight: "run",
};

const JOYSTICK_DEADZONE = 0.3;

/** Maps a virtual joystick (x right, y down, each -1..1) onto the same key state the keyboard produces. */
export const joystickToKeys = (x: number, y: number, isRunning: boolean): KeyState => ({
  up: y < -JOYSTICK_DEADZONE,
  down: y > JOYSTICK_DEADZONE,
  left: x < -JOYSTICK_DEADZONE,
  right: x > JOYSTICK_DEADZONE,
  run: isRunning,
});

export const mergeKeys = (a: KeyState, b: KeyState): KeyState => ({
  up: a.up || b.up,
  down: a.down || b.down,
  left: a.left || b.left,
  right: a.right || b.right,
  run: a.run || b.run,
});
