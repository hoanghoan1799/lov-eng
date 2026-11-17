/**
 * Minimal profanity filter for the prototype. A real deployment needs a larger,
 * maintained list for English and Vietnamese plus evasion handling.
 */
const BLOCKED_WORDS = [
  "fuck",
  "shit",
  "bitch",
  "asshole",
  "cunt",
  "dm",
  "vcl",
  "dit",
  "lon",
  "cac",
];

const BLOCKED_PATTERN = new RegExp(
  `(?<![\\p{L}\\p{N}])(${BLOCKED_WORDS.join("|")})(?![\\p{L}\\p{N}])`,
  "giu",
);

export const filterChatText = (text: string): string =>
  text.replace(BLOCKED_PATTERN, (match) => "*".repeat(match.length));

/** Collapses whitespace so chat cannot be padded with blank space. */
export const cleanChatText = (text: string): string => text.replace(/\s+/g, " ").trim();
