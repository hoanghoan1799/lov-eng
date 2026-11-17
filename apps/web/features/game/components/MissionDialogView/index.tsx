import type { MissionUiState } from "@/features/game/types/game";

export interface MissionDialogViewProps {
  mission: MissionUiState;
  typedText: string;
  heardText: string;
  isListening: boolean;
  isMicUnavailable: boolean;
  canType: boolean;
  onTypedChange: (text: string) => void;
  onMicDown: () => void;
  onMicUp: () => void;
  onSubmitTyped: () => void;
  onClose: () => void;
}

const STAR = "★";

export const MissionDialogView = ({
  mission,
  typedText,
  heardText,
  isListening,
  isMicUnavailable,
  canType,
  onTypedChange,
  onMicDown,
  onMicUp,
  onSubmitTyped,
  onClose,
}: MissionDialogViewProps) => {
  const { prompt, result } = mission;

  return (
    <div className="mission-dialog" role="dialog" aria-label="Mission">
      <button type="button" className="mission-close" onClick={onClose} aria-label="Close">
        ×
      </button>
      {result ? (
        <div className="mission-result">
          <h2>Mission complete!</h2>
          <p className="mission-stars">{STAR.repeat(result.stars)}</p>
          <p>+{result.xpGained} XP</p>
          <button type="button" className="primary" onClick={onClose}>
            Continue
          </button>
        </div>
      ) : null}
      {prompt && !result ? (
        <>
          <p className="mission-title">
            {prompt.title.en} · {prompt.turnIndex + 1}/{prompt.turnCount}
          </p>
          <p className="npc-line">{prompt.npcLine}</p>
          <p className="npc-translation">{prompt.translation}</p>
          {mission.hint ? <p className="mission-hint">{mission.hint}</p> : null}
          {heardText ? <p className="heard">You said: “{heardText}”</p> : null}
          {mission.lastPassed === false ? <p className="try-again">Not quite. Try again! (score {Math.round((mission.lastScore ?? 0) * 100)}%)</p> : null}
          {mission.error ? <p className="try-again">Speak a few times first, or turn on your microphone.</p> : null}
          <div className="mission-actions">
            <button
              type="button"
              className={`mic ${isListening ? "listening" : ""}`}
              onPointerDown={onMicDown}
              onPointerUp={onMicUp}
              onPointerLeave={onMicUp}
              disabled={isMicUnavailable}
            >
              {isListening ? "Listening…" : "🎤 Hold to speak"}
            </button>
          </div>
          {isMicUnavailable ? <p className="mic-note">Microphone is not available. You can type your answer.</p> : null}
          {canType ? (
            <form
              className="typed-form"
              onSubmit={(event) => {
                event.preventDefault();
                onSubmitTyped();
              }}
            >
              <input value={typedText} onChange={(event) => onTypedChange(event.target.value)} placeholder="Type your answer in English" maxLength={200} />
              <button type="submit">Send</button>
            </form>
          ) : null}
        </>
      ) : null}
    </div>
  );
};
