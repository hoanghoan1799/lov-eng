export const MODEL_URLS = {
  island: "/models/island.glb",
  islandLite: "/models/island-lite.glb",
  boy: "/models/boy.glb",
  girl: "/models/girl.glb",
} as const;

export const SERVER_URL = process.env.NEXT_PUBLIC_GAME_SERVER_URL ?? "ws://localhost:2567";

export const STORAGE_KEYS = {
  playerKey: "park-player-key",
  profile: "park-profile",
} as const;

export const ANIMATION = {
  idle: "Idle",
  walk: "Walk",
  run: "Run",
  fade: 0.2,
} as const;

/** Palette texture cells recoloured per player (see assets/characters/*.palette.json). */
export const PALETTE_CELL_PX = 8;
export const PALETTE_CELLS = { hair: 11, brow: 12, top: 13, topShade: 14 } as const;

export const WALK_SPEED_THRESHOLD = 0.3;
export const RUN_SPEED_THRESHOLD = 7;

export const CAMERA = {
  distance: 11,
  height: 5,
  lookHeight: 1.4,
  minPitch: 0.15,
  maxPitch: 1.2,
  defaultPitch: 0.62,
  dragSpeed: 0.005,
  smoothing: 8,
} as const;

/** Snap to the server position when the local prediction drifts this far. */
export const RECONCILE_DISTANCE = 1.5;
export const RECONCILE_RATE = 6;
export const INTERPOLATION_RATE = 12;

export const NAME_TAG_HEIGHT = 1.9;
export const NPC_SKIN_TOPS = ["#e67e22", "#16a085", "#8e44ad", "#c0392b", "#2980b9", "#27ae60", "#d35400", "#7f8c8d", "#f39c12", "#1abc9c"] as const;
export const NPC_HAIRS = ["#2c1b10", "#6b3e1e", "#111111", "#a0522d", "#3b2a20"] as const;

export const PROFILE_COLORS = {
  tops: ["#2e86de", "#f78fb3", "#e74c3c", "#27ae60", "#f1c40f", "#8e44ad", "#ecf0f1", "#2d3436"],
  hairs: ["#4a3525", "#111111", "#a0522d", "#e8c26a", "#c0392b", "#7f8c8d"],
} as const;

export const MIC_UNAVAILABLE_ERRORS = ["not-allowed", "service-not-allowed", "audio-capture", "no-speech-api"] as const;
export const SPEECH_LANG = "en-US";

export const SPEAK_HINT = "Hold the mic button and speak in English.";
export const GAME_TITLE = "Park English";
