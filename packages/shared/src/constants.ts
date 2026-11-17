export const PARK_ROOM = "park";
/** Players per room instance. The park is the shared hub, so rooms fill up before a new one opens. */
export const MAX_PARK_PLAYERS = 20;

/** Server snapshot rate and client intent send rate, in Hz. */
export const TICK_HZ = 15;

/** Walking and running speed in metres per second. */
export const PLAYER_SPEED = 5.5;
export const RUN_SPEED = 8.5;

/** The old single-park radius, kept for the movement helpers used by tests. */
export const PARK_RADIUS = 24;

/** The server stops a player whose last move message is older than this. */
export const INTENT_TTL_MS = 500;

export const MAX_NAME_LENGTH = 20;
export const DEFAULT_NAME = "Guest";

export const MAX_CHAT_LENGTH = 140;
export const CHAT_MIN_INTERVAL_MS = 800;
export const CHAT_BUBBLE_MS = 6000;
export const EMOTE_DISPLAY_MS = 3000;
export const REPORT_CONTEXT_MS = 60_000;
/** Chat is only delivered to players within this many metres. */
export const CHAT_RANGE = 25;

/** Learners must be at least this old. */
export const MIN_AGE = 18;

/** Failed attempts before the mission shows the hint sentence. */
export const HINT_AFTER_ATTEMPTS = 3;
/** Failed attempts before typing replaces speaking for that turn. */
export const TYPED_FALLBACK_AFTER_ATTEMPTS = 5;
/** A player must stand this close to an NPC to start or continue its mission. */
export const NPC_INTERACT_RANGE = 6;

export const MSG = {
  move: "move",
  snapshot: "snapshot",
  chat: "chat",
  emote: "emote",
  report: "report",
  progress: "progress",
  missionStart: "mission-start",
  missionPrompt: "mission-prompt",
  utterance: "utterance",
  turnResult: "turn-result",
  missionComplete: "mission-complete",
  notice: "notice",
} as const;

export const ERROR_CODES = {
  invalidOptions: 4001,
  underage: 4003,
} as const;
