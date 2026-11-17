import { readdirSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { type Mission, missionSchema, pathFileSchema } from "@park/shared";

import { MISSIONS } from "../src";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const MISSIONS_DIR = join(ROOT, "missions");

const errors: string[] = [];
const warnings: string[] = [];

const readJson = (file: string): unknown => JSON.parse(readFileSync(file, "utf8"));

const pathResult = pathFileSchema.safeParse(readJson(join(ROOT, "path.json")));

if (!pathResult.success) {
  console.error("path.json is invalid:");
  console.error(pathResult.error.issues.map((issue) => `  - ${issue.message}`).join("\n"));
  process.exit(1);
}

const missions = new Map<string, Mission>();

for (const file of readdirSync(MISSIONS_DIR).filter((name) => name.endsWith(".json"))) {
  const result = missionSchema.safeParse(readJson(join(MISSIONS_DIR, file)));

  if (!result.success) {
    errors.push(`${file}: ${result.error.issues.map((issue) => issue.message).join("; ")}`);
    continue;
  }

  if (missions.has(result.data.id)) {
    errors.push(`${file}: duplicate mission id ${result.data.id}`);
  }

  if (`${result.data.id}.json` !== file) {
    errors.push(`${file}: file name must match mission id ${result.data.id}`);
  }

  missions.set(result.data.id, result.data);
}

const referenced = new Set<string>();

for (const destination of pathResult.data.destinations) {
  if (destination.missions.length === 0) {
    warnings.push(`${destination.id} (${destination.phase}) has no missions yet`);
  }

  for (const missionId of destination.missions) {
    referenced.add(missionId);

    const mission = missions.get(missionId);

    if (!mission) {
      errors.push(`${destination.id} lists missing mission ${missionId}`);
    } else if (mission.destinationId !== destination.id) {
      errors.push(`${missionId} belongs to ${mission.destinationId}, not ${destination.id}`);
    }
  }
}

for (const id of missions.keys()) {
  if (!referenced.has(id)) {
    errors.push(`mission ${id} is not listed in path.json`);
  }
}

for (const id of missions.keys()) {
  if (!(id in MISSIONS)) {
    errors.push(`mission ${id} is not registered in src/index.ts`);
  }
}

warnings.forEach((message) => console.warn(`warn: ${message}`));

if (errors.length > 0) {
  console.error(errors.map((message) => `error: ${message}`).join("\n"));
  process.exit(1);
}

console.log(
  `content ok: ${pathResult.data.destinations.length} destinations, ${missions.size} missions`,
);
