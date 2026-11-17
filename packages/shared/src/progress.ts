import type { Destination, PathFile } from "./path";

export interface PlayerProgress {
  completedMissionIds: string[];
  /** Best star rating (1 to 3) per mission id. */
  stars: Record<string, number>;
  xp: number;
  /** Destinations opened through a skip challenge. */
  bypassedIds: string[];
}

export const createEmptyProgress = (): PlayerProgress => ({
  completedMissionIds: [],
  stars: {},
  xp: 0,
  bypassedIds: [],
});

/**
 * Records a finished mission. XP is paid only the first time; replays can only
 * raise the star rating.
 */
export const applyMissionResult = (
  progress: PlayerProgress,
  missionId: string,
  stars: number,
  xpGained: number,
): PlayerProgress => {
  const isFirstCompletion = !progress.completedMissionIds.includes(missionId);

  return {
    ...progress,
    completedMissionIds: isFirstCompletion
      ? [...progress.completedMissionIds, missionId]
      : progress.completedMissionIds,
    stars: { ...progress.stars, [missionId]: Math.max(progress.stars[missionId] ?? 0, stars) },
    xp: isFirstCompletion ? progress.xp + xpGained : progress.xp,
  };
};

/** A destination is complete when it has missions and all of them are done. */
export const isDestinationComplete = (
  destination: Destination,
  completedMissionIds: readonly string[],
): boolean => {
  const completed = new Set(completedMissionIds);

  return destination.missions.length > 0 && destination.missions.every((id) => completed.has(id));
};

/**
 * The hub is always open. Each later destination opens when the previous one is
 * complete, or when the learner passed its skip challenge (`bypassedIds`).
 */
export const getUnlockedDestinationIds = (
  path: PathFile,
  completedMissionIds: readonly string[],
  bypassedIds: readonly string[] = [],
): string[] => {
  const bypassed = new Set(bypassedIds);
  const sorted = [...path.destinations].sort((a, b) => a.order - b.order);
  const unlocked: string[] = [];

  sorted.forEach((destination, index) => {
    const previous = sorted[index - 1];
    const isOpen =
      index === 0 ||
      bypassed.has(destination.id) ||
      (previous !== undefined && isDestinationComplete(previous, completedMissionIds));

    if (isOpen) {
      unlocked.push(destination.id);
    }
  });

  return unlocked;
};
