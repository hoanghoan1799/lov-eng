import { MIN_AGE } from "./constants";

/**
 * Age check from a self-declared birth year. Year precision only: someone who
 * turns 18 later this year passes. Real verification is a later milestone.
 */
export const isAdult = (birthYear: number, now: Date = new Date()): boolean =>
  now.getFullYear() - birthYear >= MIN_AGE;
