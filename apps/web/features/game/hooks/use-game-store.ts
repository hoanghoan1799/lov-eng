import { create } from "zustand";

import type { ChatLine, ConnectionStatus, MissionUiState, Profile, ProgressState, RemotePlayer } from "@/features/game/types/game";

const MAX_CHAT_LINES = 60;

export const EMPTY_MISSION: MissionUiState = {
  prompt: null,
  attempts: 0,
  hint: null,
  lastScore: null,
  lastPassed: null,
  error: null,
  result: null,
};

interface GameState {
  status: ConnectionStatus;
  errorMessage: string | null;
  profile: Profile | null;
  selfId: string | null;
  /** Ids only: positions live in `liveState` so 15 Hz snapshots do not re-render React. */
  playerIds: string[];
  chat: ChatLine[];
  notice: string | null;
  progressState: ProgressState | null;
  isMissionOpen: boolean;
  mission: MissionUiState;
  isTyping: boolean;
  setStatus: (status: ConnectionStatus, errorMessage?: string | null) => void;
  setProfile: (profile: Profile | null) => void;
  setSelfId: (id: string | null) => void;
  setPlayerIds: (ids: string[]) => void;
  addChat: (line: ChatLine) => void;
  setNotice: (text: string | null) => void;
  setProgressState: (state: ProgressState) => void;
  setMissionOpen: (isOpen: boolean) => void;
  patchMission: (patch: Partial<MissionUiState>) => void;
  resetMission: () => void;
  setTyping: (isTyping: boolean) => void;
}

export const useGameStore = create<GameState>((set) => ({
  status: "idle",
  errorMessage: null,
  profile: null,
  selfId: null,
  playerIds: [],
  chat: [],
  notice: null,
  progressState: null,
  isMissionOpen: false,
  mission: EMPTY_MISSION,
  isTyping: false,
  setStatus: (status, errorMessage = null) => set({ status, errorMessage }),
  setProfile: (profile) => set({ profile }),
  setSelfId: (selfId) => set({ selfId }),
  setPlayerIds: (playerIds) => set({ playerIds }),
  addChat: (line) => set((state) => ({ chat: [...state.chat, line].slice(-MAX_CHAT_LINES) })),
  setNotice: (notice) => set({ notice }),
  setProgressState: (progressState) => set({ progressState }),
  setMissionOpen: (isMissionOpen) => set({ isMissionOpen }),
  patchMission: (patch) => set((state) => ({ mission: { ...state.mission, ...patch } })),
  resetMission: () => set({ mission: EMPTY_MISSION }),
  setTyping: (isTyping) => set({ isTyping }),
}));

/** Mutable, non-reactive live data read inside the render loop. */
export const liveState = {
  players: new Map<string, RemotePlayer>(),
  /** Latest chat bubble per player id, with expiry. */
  bubbles: new Map<string, { text: string; until: number }>(),
  /** Active emote per player id, with expiry. */
  emotes: new Map<string, { emote: string; until: number }>(),
  self: { x: 0, z: 0, ry: 0, hasSpawned: false },
};

if (typeof window !== "undefined" && process.env.NODE_ENV !== "production") {
  (window as unknown as { __park: unknown }).__park = { liveState, store: useGameStore };
}
