import { type MutableRefObject, useEffect, useRef } from "react";

import { KEY_BINDINGS, type KeyState } from "@/features/game/utils/input";

const EDITABLE_TAGS = ["INPUT", "TEXTAREA", "SELECT"];

export const isEditingText = (): boolean => EDITABLE_TAGS.includes(document.activeElement?.tagName ?? "");

/** Tracks WASD / arrow keys and Shift. Ignored while the player is typing in a text field. */
export const useKeyboardInput = (): MutableRefObject<KeyState> => {
  const keysRef = useRef<KeyState>({ up: false, down: false, left: false, right: false, run: false });

  useEffect(() => {
    const handleKey = (isDown: boolean) => (event: KeyboardEvent) => {
      const binding = KEY_BINDINGS[event.code];

      if (!binding || (isDown && isEditingText())) {
        return;
      }

      if (binding !== "run") {
        event.preventDefault();
      }

      keysRef.current[binding] = isDown;
    };
    const handleDown = handleKey(true);
    const handleUp = handleKey(false);
    const handleBlur = () => {
      keysRef.current = { up: false, down: false, left: false, right: false, run: false };
    };

    window.addEventListener("keydown", handleDown);
    window.addEventListener("keyup", handleUp);
    window.addEventListener("blur", handleBlur);

    return () => {
      window.removeEventListener("keydown", handleDown);
      window.removeEventListener("keyup", handleUp);
      window.removeEventListener("blur", handleBlur);
    };
  }, []);

  return keysRef;
};
