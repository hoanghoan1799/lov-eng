import type { AvatarLook, MissionPromptMessage, PlayerProgress } from "@park/shared";

export interface Profile {
  name: string;
  birthYear: number;
  look: AvatarLook;
}

export type ConnectionStatus = "idle" | "connecting" | "connected" | "error";

export interface ChatLine {
  id: string;
  playerId: string;
  name: string;
  text: string;
  t: number;
}

export interface RemotePlayer {
  id: string;
  name: string;
  look: AvatarLook;
  x: number;
  z: number;
  ry: number;
  speed: number;
}

export interface MissionUiState {
  prompt: MissionPromptMessage | null;
  attempts: number;
  hint: string | null;
  lastScore: number | null;
  lastPassed: boolean | null;
  error: string | null;
  result: { stars: number; xpGained: number } | null;
}

export interface ProgressState {
  progress: PlayerProgress;
  unlockedIds: string[];
}
