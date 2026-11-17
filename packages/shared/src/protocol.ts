import { z } from "zod";

import { DEFAULT_NAME, MAX_CHAT_LENGTH, MAX_NAME_LENGTH } from "./constants";

export const EMOTES = ["wave", "clap", "laugh", "think", "dance", "heart"] as const;
export type Emote = (typeof EMOTES)[number];

export const REPORT_REASONS = ["harassment", "spam", "inappropriate", "other"] as const;
export type ReportReason = (typeof REPORT_REASONS)[number];

export const GENDERS = ["boy", "girl"] as const;
export type Gender = (typeof GENDERS)[number];

export const DEFAULT_LOOK = { gender: "boy", top: "#2e86de", hair: "#4a3525" } as const;

/** Strips control characters, trims and caps the length of a display name. */
export const sanitizeName = (raw: unknown): string => {
  if (typeof raw !== "string") {
    return DEFAULT_NAME;
  }

  // eslint-disable-next-line no-control-regex
  const cleaned = raw.replace(/[\u0000-\u001f\u007f]/g, "").trim().slice(0, MAX_NAME_LENGTH);

  return cleaned.length > 0 ? cleaned : DEFAULT_NAME;
};

const colorSchema = z.string().regex(/^#[0-9a-fA-F]{6}$/);
const playerKeySchema = z.string().min(8).max(64);

export const avatarLookSchema = z.object({
  gender: z.enum(GENDERS),
  top: colorSchema,
  hair: colorSchema,
  /** Trousers or skirt colour; the model default when absent. */
  bottom: colorSchema.optional(),
  shoes: colorSchema.optional(),
});

export type AvatarLook = z.infer<typeof avatarLookSchema>;

export const parkJoinOptionsSchema = z.object({
  name: z.unknown().transform(sanitizeName),
  playerKey: playerKeySchema,
  look: avatarLookSchema.default({ ...DEFAULT_LOOK }),
  birthYear: z.number().int().min(1900).max(2100),
});

export const moveMessageSchema = z.object({
  x: z.number().min(-1).max(1),
  z: z.number().min(-1).max(1),
  run: z.boolean().default(false),
  seq: z.number().int().nonnegative(),
});

export const chatMessageSchema = z.object({
  text: z.string().min(1).max(MAX_CHAT_LENGTH),
});

export const emoteMessageSchema = z.object({
  emote: z.enum(EMOTES),
});

export const reportMessageSchema = z.object({
  targetId: z.string().min(1).max(64),
  reason: z.enum(REPORT_REASONS),
});

export const missionStartMessageSchema = z.object({
  missionId: z.string().min(1).max(80),
});

export const utteranceMessageSchema = z.object({
  text: z.string().min(1).max(200),
  source: z.enum(["voice", "typed"]),
  isMicUnavailable: z.boolean().optional(),
});

export type MoveMessage = z.infer<typeof moveMessageSchema>;
export type ParkJoinOptions = z.infer<typeof parkJoinOptionsSchema>;

export interface PlayerSnapshot {
  id: string;
  name: string;
  look: AvatarLook;
  x: number;
  z: number;
  /** Facing angle around the Y axis, in radians. */
  ry: number;
  /** Current speed in m/s, so clients can pick the idle, walk or run animation. */
  speed: number;
}

export interface SnapshotMessage {
  t: number;
  players: PlayerSnapshot[];
}

export interface ChatEvent {
  id: string;
  name: string;
  text: string;
  t: number;
}

export interface EmoteEvent {
  id: string;
  emote: Emote;
}

export interface NoticeMessage {
  text: string;
}
