import { Client, type Room } from "@colyseus/sdk";
import {
  CHAT_BUBBLE_MS,
  type ChatEvent,
  type Emote,
  EMOTE_DISPLAY_MS,
  type EmoteEvent,
  type MissionCompleteMessage,
  type MissionPromptMessage,
  MSG,
  type NoticeMessage,
  PARK_ROOM,
  type PlayerProgress,
  type ReportReason,
  type SnapshotMessage,
  type TurnResultMessage,
} from "@park/shared";

import { SERVER_URL } from "@/features/game/constants/game";
import { EMPTY_MISSION, liveState, useGameStore } from "@/features/game/hooks/use-game-store";
import type { Profile } from "@/features/game/types/game";

let room: Room | null = null;

const handleSnapshot = (snapshot: SnapshotMessage) => {
  const store = useGameStore.getState();
  const seen = new Set<string>();

  snapshot.players.forEach((player) => {
    seen.add(player.id);
    liveState.players.set(player.id, player);

    if (player.id === store.selfId && !liveState.self.hasSpawned) {
      liveState.self = { x: player.x, z: player.z, ry: player.ry, hasSpawned: true };
    }
  });

  let hasChanged = false;

  liveState.players.forEach((_player, id) => {
    if (!seen.has(id)) {
      liveState.players.delete(id);
      hasChanged = true;
    }
  });

  const ids = snapshot.players.map((player) => player.id).sort();
  const known = store.playerIds;

  if (hasChanged || ids.length !== known.length || ids.some((id, index) => id !== known[index])) {
    store.setPlayerIds(ids);
  }
};

const handleChat = (event: ChatEvent) => {
  const now = Date.now();

  liveState.bubbles.set(event.id, { text: event.text, until: now + CHAT_BUBBLE_MS });
  useGameStore.getState().addChat({ id: `${event.id}-${event.t}`, playerId: event.id, name: event.name, text: event.text, t: event.t });
};

const handleEmote = (event: EmoteEvent) => {
  liveState.emotes.set(event.id, { emote: event.emote, until: Date.now() + EMOTE_DISPLAY_MS });
};

const handleTurnResult = (result: TurnResultMessage) => {
  useGameStore.getState().patchMission({
    attempts: result.attempts,
    hint: result.hint,
    lastScore: result.score,
    lastPassed: result.isPassed,
    error: result.error,
  });
};

const handlePrompt = (prompt: MissionPromptMessage) => {
  const store = useGameStore.getState();

  store.patchMission({ ...EMPTY_MISSION, prompt, attempts: 0 });
  store.setMissionOpen(true);
};

const handleComplete = (message: MissionCompleteMessage) => {
  useGameStore.getState().patchMission({ result: { stars: message.stars, xpGained: message.xpGained }, prompt: null });
};

const isLocalUrl = (url: string): boolean => /\/\/(localhost|127\.0\.0\.1)/.test(url);

const describeConnectionError = (error: unknown): string => {
  const isRemotePage = !["localhost", "127.0.0.1"].includes(window.location.hostname);

  if (isRemotePage && isLocalUrl(SERVER_URL)) {
    return "The game server address is not set. Deploy the game server and set NEXT_PUBLIC_GAME_SERVER_URL (see docs/DEPLOY.md).";
  }

  if (error instanceof TypeError) {
    return `Cannot reach the game server at ${SERVER_URL}. Check that it is running and that the address uses wss:// on https pages.`;
  }

  return error instanceof Error ? error.message : "Could not connect to the game server";
};

export const connect = async (profile: Profile, playerKey: string) => {
  const store = useGameStore.getState();

  store.setStatus("connecting");
  store.setProfile(profile);

  try {
    const client = new Client(SERVER_URL);
    const joined = await client.joinOrCreate(PARK_ROOM, { ...profile, playerKey });

    room = joined;
    store.setSelfId(joined.sessionId);
    joined.onMessage(MSG.snapshot, handleSnapshot);
    joined.onMessage(MSG.chat, handleChat);
    joined.onMessage(MSG.emote, handleEmote);
    joined.onMessage(MSG.notice, (message: NoticeMessage) => store.setNotice(message.text));
    joined.onMessage(MSG.progress, (payload: { progress: PlayerProgress; unlockedIds: string[] }) => store.setProgressState(payload));
    joined.onMessage(MSG.missionPrompt, handlePrompt);
    joined.onMessage(MSG.turnResult, handleTurnResult);
    joined.onMessage(MSG.missionComplete, handleComplete);
    joined.onLeave(() => {
      room = null;
      useGameStore.getState().setStatus("error", "Disconnected from the server");
    });
    store.setStatus("connected");
  } catch (error) {
    store.setStatus("error", describeConnectionError(error));
  }
};

export const sendMove = (x: number, z: number, run: boolean, seq: number) => room?.send(MSG.move, { x, z, run, seq });
export const sendChat = (text: string) => room?.send(MSG.chat, { text });
export const sendEmote = (emote: Emote) => room?.send(MSG.emote, { emote });
export const sendReport = (targetId: string, reason: ReportReason) => room?.send(MSG.report, { targetId, reason });
export const sendMissionStart = (missionId: string) => room?.send(MSG.missionStart, { missionId });
export const sendUtterance = (text: string, source: "voice" | "typed", isMicUnavailable: boolean) =>
  room?.send(MSG.utterance, { text, source, isMicUnavailable });
export const disconnect = () => {
  room?.leave();
  room = null;
};
