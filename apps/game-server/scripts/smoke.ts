import { Client } from "@colyseus/sdk";
import { MSG, PARK_ROOM, type SnapshotMessage } from "@park/shared";

const URL = process.env.SERVER_URL ?? "ws://localhost:2567";
const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

const join = async (name: string, birthYear = 1990) => {
  const client = new Client(URL);

  return client.joinOrCreate(PARK_ROOM, {
    name,
    playerKey: `smoke-key-${name}-12345`,
    look: { gender: "girl", top: "#ff6699", hair: "#222222" },
    birthYear,
  });
};

const check = (label: string, ok: boolean) => {
  console.log(`${ok ? "PASS" : "FAIL"} ${label}`);

  if (!ok) {
    process.exitCode = 1;
  }
};

const run = async () => {
  const a = await join("Ann");
  const b = await join("Bob");
  let last: SnapshotMessage | null = null;
  const chats: string[] = [];

  a.onMessage(MSG.snapshot, (m: SnapshotMessage) => {
    last = m;
  });
  b.onMessage(MSG.chat, (m: { text: string }) => chats.push(m.text));
  await sleep(400);
  check("two players see each other", (last as SnapshotMessage | null)?.players.length === 2);

  const before = (last as SnapshotMessage | null)?.players.find((p) => p.id === a.sessionId);

  for (let i = 0; i < 10; i += 1) {
    a.send(MSG.move, { x: 1, z: 0, run: false, seq: i });
    await sleep(60);
  }

  const after = (last as SnapshotMessage | null)?.players.find((p) => p.id === a.sessionId);

  check("move changes position", !!before && !!after && after.x > before.x + 1);

  a.send(MSG.chat, { text: "hello shit world" });
  await sleep(300);
  check("nearby chat delivered and filtered", chats[0] === "hello **** world");

  let prompt = "";
  let turns = 0;
  let complete = false;

  a.onMessage(MSG.missionPrompt, (m: { npcLine: string }) => {
    prompt = m.npcLine;
  });
  a.onMessage(MSG.turnResult, (m: { isPassed: boolean }) => {
    turns += m.isPassed ? 1 : 0;
  });
  a.onMessage(MSG.missionComplete, () => {
    complete = true;
  });
  a.send(MSG.missionStart, { missionId: "park-greeting" });
  await sleep(200);
  check("mission refused when far from NPC", prompt === "");

  let under = false;

  try {
    await join("Kid", new Date().getFullYear() - 10);
  } catch {
    under = true;
  }

  check("under-18 join rejected", under);

  a.leave();
  b.leave();
  void turns;
  void complete;
};

run().then(() => process.exit(process.exitCode ?? 0));
