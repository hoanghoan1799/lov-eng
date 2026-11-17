import { useCallback, useState } from "react";

import { useGameStore } from "@/features/game/hooks/use-game-store";
import { useSpeechRecognition } from "@/features/game/hooks/use-speech-recognition";
import { sendUtterance } from "@/features/game/services/connection";
import { canTypeAnswer } from "@/features/game/utils/missions";

export const useMissionDialog = () => {
  const isOpen = useGameStore((state) => state.isMissionOpen);
  const mission = useGameStore((state) => state.mission);
  const setMissionOpen = useGameStore((state) => state.setMissionOpen);
  const resetMission = useGameStore((state) => state.resetMission);
  const patchMission = useGameStore((state) => state.patchMission);
  const [typedText, setTypedText] = useState("");
  const [heardText, setHeardText] = useState("");
  const [isMicBroken, setIsMicBroken] = useState(false);

  const handleHeard = useCallback(
    (text: string) => {
      setHeardText(text);
      sendUtterance(text, "voice", false);
    },
    [],
  );
  const { isListening, isMicUnavailable, start, stop } = useSpeechRecognition(handleHeard);
  const isMicOff = isMicUnavailable || isMicBroken;
  const canType = canTypeAnswer(mission.attempts, isMicOff);

  const handleMicDown = () => {
    patchMission({ error: null });
    start();
  };

  const handleSubmitTyped = () => {
    const text = typedText.trim();

    if (text.length === 0) {
      return;
    }

    sendUtterance(text, "typed", isMicOff);
    setHeardText(text);
    setTypedText("");
  };

  const handleClose = () => {
    setMissionOpen(false);
    resetMission();
    setTypedText("");
    setHeardText("");
    setIsMicBroken(false);
  };

  return {
    isOpen,
    mission,
    typedText,
    heardText,
    isListening,
    isMicUnavailable: isMicOff,
    canType,
    onTypedChange: setTypedText,
    onMicDown: handleMicDown,
    onMicUp: stop,
    onSubmitTyped: handleSubmitTyped,
    onClose: handleClose,
    onMarkMicBroken: () => setIsMicBroken(true),
  };
};
