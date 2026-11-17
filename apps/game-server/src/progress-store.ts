import { existsSync, mkdirSync, readFileSync, renameSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";

import { createEmptyProgress, type PlayerProgress } from "@park/shared";

const SAVE_DELAY_MS = 500;

/** Progress per anonymous player key, kept in one JSON file (swap for a database later). */
export class ProgressStore {
  private readonly data = new Map<string, PlayerProgress>();

  private timer: NodeJS.Timeout | null = null;

  public constructor(private readonly filePath: string) {
    if (existsSync(filePath)) {
      const raw = JSON.parse(readFileSync(filePath, "utf8")) as Record<string, PlayerProgress>;

      Object.entries(raw).forEach(([key, progress]) => this.data.set(key, progress));
    }
  }

  public get = (playerKey: string): PlayerProgress => this.data.get(playerKey) ?? createEmptyProgress();

  public set = (playerKey: string, progress: PlayerProgress) => {
    this.data.set(playerKey, progress);
    this.scheduleSave();
  };

  public flush = () => {
    if (this.timer) {
      clearTimeout(this.timer);
      this.timer = null;
    }

    mkdirSync(dirname(this.filePath), { recursive: true });

    const temporary = `${this.filePath}.tmp`;

    writeFileSync(temporary, JSON.stringify(Object.fromEntries(this.data)));
    renameSync(temporary, this.filePath);
  };

  private scheduleSave = () => {
    if (!this.timer) {
      this.timer = setTimeout(this.flush, SAVE_DELAY_MS);
    }
  };
}
