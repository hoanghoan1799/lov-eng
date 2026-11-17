import { useCallback, useEffect, useRef, useState } from "react";

import { MIC_UNAVAILABLE_ERRORS, SPEECH_LANG } from "@/features/game/constants/game";

interface RecognitionResultEvent {
  results: ArrayLike<ArrayLike<{ transcript: string }>>;
}

interface RecognitionErrorEvent {
  error: string;
}

interface Recognition {
  lang: string;
  interimResults: boolean;
  maxAlternatives: number;
  onresult: ((event: RecognitionResultEvent) => void) | null;
  onerror: ((event: RecognitionErrorEvent) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
}

type RecognitionConstructor = new () => Recognition;

const getRecognitionConstructor = (): RecognitionConstructor | null => {
  const scope = window as unknown as { SpeechRecognition?: RecognitionConstructor; webkitSpeechRecognition?: RecognitionConstructor };

  return scope.SpeechRecognition ?? scope.webkitSpeechRecognition ?? null;
};

/** Browser speech-to-text for one utterance at a time. */
export const useSpeechRecognition = (onResult: (text: string) => void) => {
  const recognitionRef = useRef<Recognition | null>(null);
  const [isListening, setIsListening] = useState(false);
  const [isMicUnavailable, setIsMicUnavailable] = useState(false);

  useEffect(() => {
    if (!getRecognitionConstructor()) {
      setIsMicUnavailable(true);
    }

    return () => recognitionRef.current?.stop();
  }, []);

  const start = useCallback(() => {
    const Constructor = getRecognitionConstructor();

    if (!Constructor) {
      setIsMicUnavailable(true);

      return;
    }

    const recognition = new Constructor();

    recognition.lang = SPEECH_LANG;
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.onresult = (event) => {
      const text = event.results[0]?.[0]?.transcript;

      if (text) {
        onResult(text);
      }
    };
    recognition.onerror = (event) => {
      if ((MIC_UNAVAILABLE_ERRORS as readonly string[]).includes(event.error)) {
        setIsMicUnavailable(true);
      }

      setIsListening(false);
    };
    recognition.onend = () => setIsListening(false);
    recognitionRef.current = recognition;
    setIsListening(true);
    recognition.start();
  }, [onResult]);

  const stop = useCallback(() => recognitionRef.current?.stop(), []);

  return { isListening, isMicUnavailable, start, stop };
};
