import { type PointerEvent, useEffect, useState } from "react";

import { liveState } from "@/features/game/hooks/use-game-store";

const PAD_SIZE = 130;
const KNOB_SIZE = 54;
const MAX_OFFSET = (PAD_SIZE - KNOB_SIZE) / 2;
const TOUCH_QUERY = "(pointer: coarse)";
const FORCE_PARAM = "touch";

/** On-screen move stick and run toggle for touch screens (or `?touch=1`). */
export const Joystick = () => {
  const [isVisible, setIsVisible] = useState(false);
  const [knob, setKnob] = useState({ x: 0, y: 0 });
  const [isRunning, setIsRunning] = useState(false);

  useEffect(() => {
    const isForced = new URLSearchParams(window.location.search).get(FORCE_PARAM) === "1";

    setIsVisible(isForced || window.matchMedia(TOUCH_QUERY).matches);
  }, []);

  useEffect(() => {
    liveState.joystick.isRunning = isRunning;
  }, [isRunning]);

  const handleMove = (event: PointerEvent<HTMLDivElement>) => {
    if (!event.currentTarget.hasPointerCapture(event.pointerId)) {
      return;
    }

    const rect = event.currentTarget.getBoundingClientRect();
    let dx = event.clientX - (rect.left + rect.width / 2);
    let dy = event.clientY - (rect.top + rect.height / 2);
    const length = Math.hypot(dx, dy);

    if (length > MAX_OFFSET) {
      dx = (dx / length) * MAX_OFFSET;
      dy = (dy / length) * MAX_OFFSET;
    }

    setKnob({ x: dx, y: dy });
    liveState.joystick.x = dx / MAX_OFFSET;
    liveState.joystick.y = dy / MAX_OFFSET;
  };

  const handleDown = (event: PointerEvent<HTMLDivElement>) => {
    event.currentTarget.setPointerCapture(event.pointerId);
    handleMove(event);
  };

  const handleRelease = () => {
    setKnob({ x: 0, y: 0 });
    liveState.joystick.x = 0;
    liveState.joystick.y = 0;
  };

  if (!isVisible) {
    return null;
  }

  return (
    <>
      <div
        className="joystick"
        style={{ width: PAD_SIZE, height: PAD_SIZE }}
        onPointerDown={handleDown}
        onPointerMove={handleMove}
        onPointerUp={handleRelease}
        onPointerCancel={handleRelease}
        aria-label="Move"
      >
        <div className="joystick-knob" style={{ width: KNOB_SIZE, height: KNOB_SIZE, transform: `translate(${knob.x}px, ${knob.y}px)` }} />
      </div>
      <button type="button" className={`run-toggle ${isRunning ? "on" : ""}`} onClick={() => setIsRunning((value) => !value)}>
        {isRunning ? "Run: on" : "Run"}
      </button>
    </>
  );
};
