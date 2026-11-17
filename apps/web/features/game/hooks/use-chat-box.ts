import { type RefObject, useEffect, useRef, useState } from "react";

import { useGameStore } from "@/features/game/hooks/use-game-store";
import { isEditingText } from "@/features/game/hooks/use-keyboard-input";
import { sendChat } from "@/features/game/services/connection";

const FOCUS_KEYS = ["Enter", "KeyT"];

export const useChatBox = (): {
  inputRef: RefObject<HTMLInputElement | null>;
  text: string;
  lines: ReturnType<typeof useGameStore.getState>["chat"];
  onTextChange: (text: string) => void;
  onSubmit: () => void;
  onFocus: () => void;
  onBlur: () => void;
} => {
  const lines = useGameStore((state) => state.chat);
  const setTyping = useGameStore((state) => state.setTyping);
  const inputRef = useRef<HTMLInputElement>(null);
  const [text, setText] = useState("");

  useEffect(() => {
    const handleKey = (event: KeyboardEvent) => {
      if (FOCUS_KEYS.includes(event.code) && !isEditingText() && !useGameStore.getState().isMissionOpen) {
        event.preventDefault();
        inputRef.current?.focus();
      }

      if (event.code === "Escape") {
        inputRef.current?.blur();
      }
    };

    window.addEventListener("keydown", handleKey);

    return () => window.removeEventListener("keydown", handleKey);
  }, []);

  const handleSubmit = () => {
    const value = text.trim();

    if (value.length > 0) {
      sendChat(value);
    }

    setText("");
    inputRef.current?.blur();
  };

  return {
    inputRef,
    text,
    lines,
    onTextChange: setText,
    onSubmit: handleSubmit,
    onFocus: () => setTyping(true),
    onBlur: () => setTyping(false),
  };
};
