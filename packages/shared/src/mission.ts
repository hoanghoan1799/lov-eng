import type { Cefr, Mission, Turn } from "./path";
import type { PlayerProgress } from "./progress";
import { matchUtterance, PASS_THRESHOLD_BY_CEFR, type UtteranceMatch } from "./speech";

export type UtteranceSource = "voice" | "typed";

export interface UtteranceMessage {
  text: string;
  source: UtteranceSource;
  /** Set by the client when speech recognition is not available at all. */
  isMicUnavailable?: boolean;
}

/** What the NPC says next, sent when a mission starts and after every passed turn. */
export interface MissionPromptMessage {
  missionId: string;
  title: { vi: string; en: string };
  turnIndex: number;
  turnCount: number;
  npcLine: string;
  translation: string;
  /** Hint shown right away on a replay of a turn that already failed too often. */
  hint: string | null;
}

export interface TurnResultMessage {
  turnId: string;
  isPassed: boolean;
  score: number;
  attempts: number;
  /** Shown after enough failed attempts. */
  hint: string | null;
  nextTurnIndex: number;
  /** Set when the server refuses the message, e.g. typing before it is allowed. */
  error: string | null;
}

export interface MissionCompleteMessage {
  missionId: string;
  stars: number;
  xpGained: number;
  progress: PlayerProgress;
}

export const evaluateTurn = (turn: Turn, text: string, cefr: Cefr): UtteranceMatch =>
  matchUtterance(text, turn.accepted, PASS_THRESHOLD_BY_CEFR[cefr]);

/** 3 stars for a first-try spoken pass, 2 for a later spoken pass, 1 for typing. */
export const calculateTurnStars = (attempts: number, source: UtteranceSource): number => {
  if (source === "typed") {
    return 1;
  }

  return attempts <= 1 ? 3 : 2;
};

export const calculateMissionStars = (turnStars: readonly number[]): number => {
  if (turnStars.length === 0) {
    return 1;
  }

  const average = turnStars.reduce((sum, stars) => sum + stars, 0) / turnStars.length;

  return Math.max(1, Math.round(average));
};

export const calculateMissionXp = (mission: Mission, stars: number): number =>
  Math.ceil((mission.rewardXp * stars) / 3);
