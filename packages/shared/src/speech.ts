/**
 * Fuzzy matching between what the speech recognizer heard and the sentences a
 * mission accepts. This checks recognition ("did they say the target sentence"),
 * not pronunciation quality.
 */

export type CefrLevel = "A1" | "A2" | "B1" | "B2";

/** Minimum score to pass a turn. Lower levels are more forgiving. */
export const PASS_THRESHOLD_BY_CEFR: Record<CefrLevel, number> = {
  A1: 0.6,
  A2: 0.7,
  B1: 0.8,
  B2: 0.85,
};

const CONTRACTIONS: Record<string, string> = {
  "i'm": "i am",
  "i'd": "i would",
  "i'll": "i will",
  "i've": "i have",
  "it's": "it is",
  "that's": "that is",
  "what's": "what is",
  "you're": "you are",
  "we're": "we are",
  "can't": "cannot",
  "don't": "do not",
  "isn't": "is not",
};

export const normalizeUtterance = (text: string): string[] => {
  const words = text
    .toLowerCase()
    .replace(/[’]/g, "'")
    .replace(/[^a-z0-9'\s]/g, " ")
    .split(/\s+/)
    .filter(Boolean);

  return words.flatMap((word) => (CONTRACTIONS[word] ?? word).split(" "));
};

const charEditDistance = (a: string, b: string): number => {
  const previous = Array.from({ length: b.length + 1 }, (_, index) => index);

  for (let i = 1; i <= a.length; i += 1) {
    let diagonal = previous[0] ?? 0;
    previous[0] = i;

    for (let j = 1; j <= b.length; j += 1) {
      const above = previous[j] ?? 0;
      const cost = a[i - 1] === b[j - 1] ? 0 : 1;

      previous[j] = Math.min(above + 1, (previous[j - 1] ?? 0) + 1, diagonal + cost);
      diagonal = above;
    }
  }

  return previous[b.length] ?? 0;
};

/** Cost of treating word `a` as word `b`: 0 when equal, up to 1 when unrelated. */
const getWordCost = (a: string, b: string): number => {
  if (a === b) {
    return 0;
  }

  return charEditDistance(a, b) / Math.max(a.length, b.length);
};

const getWordEditDistance = (heard: string[], target: string[]): number => {
  const previous = Array.from({ length: target.length + 1 }, (_, index) => index);

  for (let i = 1; i <= heard.length; i += 1) {
    let diagonal = previous[0] ?? 0;
    previous[0] = i;

    for (let j = 1; j <= target.length; j += 1) {
      const above = previous[j] ?? 0;
      const cost = getWordCost(heard[i - 1] ?? "", target[j - 1] ?? "");

      previous[j] = Math.min(above + 1, (previous[j - 1] ?? 0) + 1, diagonal + cost);
      diagonal = above;
    }
  }

  return previous[target.length] ?? 0;
};

/** Similarity from 0 (nothing in common) to 1 (identical after normalizing). */
export const calculateUtteranceScore = (heard: string, target: string): number => {
  const heardWords = normalizeUtterance(heard);
  const targetWords = normalizeUtterance(target);

  if (targetWords.length === 0) {
    return 0;
  }

  const distance = getWordEditDistance(heardWords, targetWords);
  const longest = Math.max(heardWords.length, targetWords.length);

  return Math.max(0, 1 - distance / longest);
};

export interface UtteranceMatch {
  isPassed: boolean;
  score: number;
  bestMatch: string | null;
}

export const matchUtterance = (
  heard: string,
  accepted: readonly string[],
  threshold: number,
): UtteranceMatch => {
  let bestScore = 0;
  let bestMatch: string | null = null;

  for (const candidate of accepted) {
    const score = calculateUtteranceScore(heard, candidate);

    if (score > bestScore) {
      bestScore = score;
      bestMatch = candidate;
    }
  }

  return { isPassed: bestScore >= threshold, score: bestScore, bestMatch };
};
