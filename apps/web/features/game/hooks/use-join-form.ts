import { DEFAULT_LOOK, type Gender, isAdult, MIN_AGE } from "@park/shared";
import { useEffect, useState } from "react";

import { STORAGE_KEYS } from "@/features/game/constants/game";
import { connect } from "@/features/game/services/connection";
import type { Profile } from "@/features/game/types/game";

const CURRENT_YEAR = new Date().getFullYear();

const readStorage = (key: string): string | null => {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
};

const writeStorage = (key: string, value: string) => {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    // Storage can be blocked; the game still works with a fresh key each visit.
  }
};

const getPlayerKey = (): string => {
  const existing = readStorage(STORAGE_KEYS.playerKey);

  if (existing) {
    return existing;
  }

  const created = crypto.randomUUID();

  writeStorage(STORAGE_KEYS.playerKey, created);

  return created;
};

export const useJoinForm = () => {
  const [name, setName] = useState("");
  const [birthYear, setBirthYear] = useState("");
  const [gender, setGender] = useState<Gender>(DEFAULT_LOOK.gender);
  const [top, setTop] = useState<string>(DEFAULT_LOOK.top);
  const [hair, setHair] = useState<string>(DEFAULT_LOOK.hair);
  const [isSubmitted, setIsSubmitted] = useState(false);

  useEffect(() => {
    const saved = readStorage(STORAGE_KEYS.profile);

    if (!saved) {
      return;
    }

    try {
      const profile = JSON.parse(saved) as Profile;

      setName(profile.name);
      setBirthYear(String(profile.birthYear));
      setGender(profile.look.gender);
      setTop(profile.look.top);
      setHair(profile.look.hair);
    } catch {
      // Ignore a corrupted saved profile.
    }
  }, []);

  const year = Number(birthYear);
  const isYearValid = Number.isInteger(year) && year >= 1900 && year <= CURRENT_YEAR;
  const isUnderage = isYearValid && !isAdult(year);
  const canSubmit = name.trim().length > 0 && isYearValid && !isUnderage;

  const handleSubmit = () => {
    setIsSubmitted(true);

    if (!canSubmit) {
      return;
    }

    const profile: Profile = { name: name.trim(), birthYear: year, look: { gender, top, hair } };

    writeStorage(STORAGE_KEYS.profile, JSON.stringify(profile));
    void connect(profile, getPlayerKey());
  };

  return {
    name,
    birthYear,
    gender,
    top,
    hair,
    isUnderage,
    isYearInvalid: isSubmitted && !isYearValid,
    minAge: MIN_AGE,
    onNameChange: setName,
    onBirthYearChange: setBirthYear,
    onGenderChange: setGender,
    onTopChange: setTop,
    onHairChange: setHair,
    onSubmit: handleSubmit,
  };
};
