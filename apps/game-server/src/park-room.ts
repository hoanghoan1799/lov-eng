import { appendFileSync, mkdirSync } from "node:fs";
import { dirname } from "node:path";

import { MISSIONS, PATH } from "@park/content";
import {
  applyMissionResult,
  calculateMissionStars,
  calculateMissionXp,
  calculateTurnStars,
  CHAT_MIN_INTERVAL_MS,
  CHAT_RANGE,
  type ChatEvent,
  chatMessageSchema,
  cleanChatText,
  type EmoteEvent,
  emoteMessageSchema,
  ERROR_CODES,
  evaluateTurn,
  filterChatText,
  getUnlockedDestinationIds,
  HINT_AFTER_ATTEMPTS,
  INTENT_TTL_MS,
  isAdult,
  MAX_PARK_PLAYERS,
  type Mission,
  type MissionCompleteMessage,
  type MissionPromptMessage,
  missionStartMessageSchema,
  moveMessageSchema,
  MSG,
  NPC_INTERACT_RANGE,
  type ParkJoinOptions,
  parkJoinOptionsSchema,
  type PlayerSnapshot,
  REPORT_CONTEXT_MS,
  reportMessageSchema,
  RUN_SPEED,
  stepPlayer,
  TICK_HZ,
  type TurnResultMessage,
  TYPED_FALLBACK_AFTER_ATTEMPTS,
  utteranceMessageSchema,
} from "@park/shared";
import { type Client, Room, ServerError } from "colyseus";

import { ProgressStore } from "./progress-store";
import { NPC_POSITIONS, SPAWN, WORLD } from "./world";

const REPORT_LOG_PATH = process.env.REPORT_LOG ?? "data/reports.jsonl";
const PROGRESS_PATH = process.env.PROGRESS_FILE ?? "data/progress.json";

export const progressStore = new ProgressStore(PROGRESS_PATH);

interface MissionRun {
  mission: Mission;
  turnIndex: number;
  attempts: number;
  turnStars: number[];
}

interface Player {
  id: string;
  playerKey: string;
  options: ParkJoinOptions;
  x: number;
  z: number;
  ry: number;
  speed: number;
  intentX: number;
  intentZ: number;
  isRunning: boolean;
  intentAt: number;
  lastChatAt: number;
  run: MissionRun | null;
}

interface ChatLogEntry {
  t: number;
  id: string;
  name: string;
  text: string;
}

const distance = (ax: number, az: number, bx: number, bz: number) => Math.hypot(ax - bx, az - bz);

export class ParkRoom extends Room {
  public maxClients = MAX_PARK_PLAYERS;

  private readonly players = new Map<string, Player>();

  private readonly chatLog: ChatLogEntry[] = [];

  public onCreate = () => {
    this.setSimulationInterval((deltaMs) => this.tick(deltaMs), 1000 / TICK_HZ);

    this.onMessage("*", () => undefined);
    this.onMessage(MSG.move, (client, raw) => this.handleMove(client, raw));
    this.onMessage(MSG.chat, (client, raw) => this.handleChat(client, raw));
    this.onMessage(MSG.emote, (client, raw) => this.handleEmote(client, raw));
    this.onMessage(MSG.report, (client, raw) => this.handleReport(client, raw));
    this.onMessage(MSG.missionStart, (client, raw) => this.handleMissionStart(client, raw));
    this.onMessage(MSG.utterance, (client, raw) => this.handleUtterance(client, raw));
  };

  public onAuth = (_client: Client, rawOptions: unknown) => {
    const parsed = parkJoinOptionsSchema.safeParse(rawOptions);

    if (!parsed.success) {
      throw new ServerError(ERROR_CODES.invalidOptions, "Invalid join options");
    }

    if (!isAdult(parsed.data.birthYear)) {
      throw new ServerError(ERROR_CODES.underage, "This game is for adults (18+)");
    }

    return parsed.data;
  };

  public onJoin = (client: Client, _options: unknown, auth: ParkJoinOptions) => {
    this.players.set(client.sessionId, {
      id: client.sessionId,
      playerKey: auth.playerKey,
      options: auth,
      x: SPAWN.x + (Math.random() - 0.5) * 3,
      z: SPAWN.z + (Math.random() - 0.5) * 3,
      ry: 0,
      speed: 0,
      intentX: 0,
      intentZ: 0,
      isRunning: false,
      intentAt: 0,
      lastChatAt: 0,
      run: null,
    });

    client.send(MSG.progress, this.buildProgressPayload(auth.playerKey));
  };

  public onLeave = (client: Client) => {
    this.players.delete(client.sessionId);
  };

  public onDispose = () => {
    progressStore.flush();
  };

  private tick = (deltaMs: number) => {
    const now = Date.now();
    const delta = Math.min(deltaMs, 200) / 1000;
    const snapshots: PlayerSnapshot[] = [];

    this.players.forEach((player) => {
      const isMoving = now - player.intentAt < INTENT_TTL_MS && (player.intentX !== 0 || player.intentZ !== 0);

      if (isMoving) {
        const next = stepPlayer({ x: player.x, z: player.z }, { x: player.intentX, z: player.intentZ }, delta, WORLD, player.isRunning);
        const moved = distance(next.x, next.z, player.x, player.z);

        player.speed = delta > 0 ? Math.min(RUN_SPEED, moved / delta) : 0;
        player.ry = Math.atan2(player.intentX, player.intentZ);
        player.x = next.x;
        player.z = next.z;
      } else {
        player.speed = 0;
      }

      snapshots.push({
        id: player.id,
        name: player.options.name,
        look: player.options.look,
        x: Math.round(player.x * 100) / 100,
        z: Math.round(player.z * 100) / 100,
        ry: Math.round(player.ry * 100) / 100,
        speed: Math.round(player.speed * 10) / 10,
      });
    });

    this.broadcast(MSG.snapshot, { t: now, players: snapshots });
  };

  private handleMove = (client: Client, raw: unknown) => {
    const parsed = moveMessageSchema.safeParse(raw);
    const player = this.players.get(client.sessionId);

    if (!parsed.success || !player) {
      return;
    }

    player.intentX = parsed.data.x;
    player.intentZ = parsed.data.z;
    player.isRunning = parsed.data.run;
    player.intentAt = Date.now();
  };

  private handleChat = (client: Client, raw: unknown) => {
    const parsed = chatMessageSchema.safeParse(raw);
    const player = this.players.get(client.sessionId);
    const now = Date.now();

    if (!parsed.success || !player || now - player.lastChatAt < CHAT_MIN_INTERVAL_MS) {
      return;
    }

    const text = filterChatText(cleanChatText(parsed.data.text));

    if (text.length === 0) {
      return;
    }

    player.lastChatAt = now;
    this.chatLog.push({ t: now, id: player.id, name: player.options.name, text });
    this.trimChatLog(now);

    const event: ChatEvent = { id: player.id, name: player.options.name, text, t: now };

    this.clients.forEach((other) => {
      const target = this.players.get(other.sessionId);

      if (target && distance(player.x, player.z, target.x, target.z) <= CHAT_RANGE) {
        other.send(MSG.chat, event);
      }
    });
  };

  private handleEmote = (client: Client, raw: unknown) => {
    const parsed = emoteMessageSchema.safeParse(raw);

    if (parsed.success && this.players.has(client.sessionId)) {
      const event: EmoteEvent = { id: client.sessionId, emote: parsed.data.emote };

      this.broadcast(MSG.emote, event);
    }
  };

  private handleReport = (client: Client, raw: unknown) => {
    const parsed = reportMessageSchema.safeParse(raw);
    const reporter = this.players.get(client.sessionId);
    const target = parsed.success ? this.players.get(parsed.data.targetId) : undefined;

    if (!parsed.success || !reporter || !target) {
      return;
    }

    const now = Date.now();

    this.trimChatLog(now);

    const entry = {
      at: new Date(now).toISOString(),
      room: this.roomId,
      reporter: reporter.playerKey,
      target: target.playerKey,
      reason: parsed.data.reason,
      context: this.chatLog,
    };

    mkdirSync(dirname(REPORT_LOG_PATH), { recursive: true });
    appendFileSync(REPORT_LOG_PATH, `${JSON.stringify(entry)}\n`);
    client.send(MSG.notice, { text: "Thanks, your report was sent to the moderators." });
  };

  private handleMissionStart = (client: Client, raw: unknown) => {
    const parsed = missionStartMessageSchema.safeParse(raw);
    const player = this.players.get(client.sessionId);
    const mission = parsed.success ? MISSIONS[parsed.data.missionId] : undefined;

    if (!parsed.success || !player || !mission) {
      return;
    }

    const npc = NPC_POSITIONS[mission.destinationId];
    const progress = progressStore.get(player.playerKey);
    const unlocked = getUnlockedDestinationIds(PATH, progress.completedMissionIds, progress.bypassedIds);

    if (!npc || distance(player.x, player.z, npc.x, npc.z) > NPC_INTERACT_RANGE) {
      client.send(MSG.notice, { text: "Walk up to the character first." });

      return;
    }

    if (!unlocked.includes(mission.destinationId)) {
      client.send(MSG.notice, { text: "Finish the previous place to open this one." });

      return;
    }

    player.run = { mission, turnIndex: 0, attempts: 0, turnStars: [] };
    client.send(MSG.missionPrompt, this.buildPrompt(player.run));
  };

  private handleUtterance = (client: Client, raw: unknown) => {
    const parsed = utteranceMessageSchema.safeParse(raw);
    const player = this.players.get(client.sessionId);
    const run = player?.run;
    const turn = run?.mission.turns[run.turnIndex];

    if (!parsed.success || !player || !run || !turn) {
      return;
    }

    const isTypedAllowed = run.attempts >= TYPED_FALLBACK_AFTER_ATTEMPTS || parsed.data.isMicUnavailable === true;

    if (parsed.data.source === "typed" && !isTypedAllowed) {
      client.send(MSG.turnResult, this.buildResult(run, turn.id, false, 0, "typing-not-allowed"));

      return;
    }

    const match = evaluateTurn(turn, parsed.data.text, run.mission.cefr);

    run.attempts += 1;

    if (!match.isPassed) {
      client.send(MSG.turnResult, this.buildResult(run, turn.id, false, match.score, null));

      return;
    }

    run.turnStars.push(calculateTurnStars(run.attempts, parsed.data.source));
    client.send(MSG.turnResult, this.buildResult(run, turn.id, true, match.score, null));
    run.turnIndex += 1;
    run.attempts = 0;

    if (run.turnIndex < run.mission.turns.length) {
      client.send(MSG.missionPrompt, this.buildPrompt(run));

      return;
    }

    this.completeMission(client, player, run);
  };

  private completeMission = (client: Client, player: Player, run: MissionRun) => {
    const stars = calculateMissionStars(run.turnStars);
    const xpGained = calculateMissionXp(run.mission, stars);
    const progress = applyMissionResult(progressStore.get(player.playerKey), run.mission.id, stars, xpGained);
    const message: MissionCompleteMessage = { missionId: run.mission.id, stars, xpGained, progress };

    progressStore.set(player.playerKey, progress);
    player.run = null;
    client.send(MSG.missionComplete, message);
    client.send(MSG.progress, this.buildProgressPayload(player.playerKey));
  };

  private buildPrompt = (run: MissionRun): MissionPromptMessage => {
    const turn = run.mission.turns[run.turnIndex];
    const lines = turn?.npcLines ?? [""];

    return {
      missionId: run.mission.id,
      title: run.mission.title,
      turnIndex: run.turnIndex,
      turnCount: run.mission.turns.length,
      npcLine: lines[Math.floor(Math.random() * lines.length)] ?? "",
      translation: turn?.translation ?? "",
      hint: null,
    };
  };

  private buildResult = (run: MissionRun, turnId: string, isPassed: boolean, score: number, error: string | null): TurnResultMessage => {
    const turn = run.mission.turns[run.turnIndex];
    const shouldHint = !isPassed && run.attempts >= HINT_AFTER_ATTEMPTS;

    return {
      turnId,
      isPassed,
      score,
      attempts: run.attempts,
      hint: shouldHint ? (turn?.hint ?? null) : null,
      nextTurnIndex: isPassed ? run.turnIndex + 1 : run.turnIndex,
      error,
    };
  };

  private buildProgressPayload = (playerKey: string) => {
    const progress = progressStore.get(playerKey);

    return {
      progress,
      unlockedIds: getUnlockedDestinationIds(PATH, progress.completedMissionIds, progress.bypassedIds),
    };
  };

  private trimChatLog = (now: number) => {
    while (this.chatLog.length > 0 && now - (this.chatLog[0]?.t ?? now) > REPORT_CONTEXT_MS) {
      this.chatLog.shift();
    }
  };
}
