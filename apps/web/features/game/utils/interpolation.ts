/** Frame-rate independent exponential smoothing factor. */
export const calculateSmoothing = (rate: number, deltaSeconds: number): number => 1 - Math.exp(-rate * deltaSeconds);

/** Shortest-path angle interpolation. */
export const lerpAngle = (from: number, to: number, t: number): number => {
  const difference = Math.atan2(Math.sin(to - from), Math.cos(to - from));

  return from + difference * t;
};
