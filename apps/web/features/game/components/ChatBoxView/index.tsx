import type { RefObject } from "react";

import type { ChatLine } from "@/features/game/types/game";

export interface ChatBoxViewProps {
  inputRef: RefObject<HTMLInputElement | null>;
  text: string;
  lines: ChatLine[];
  onTextChange: (text: string) => void;
  onSubmit: () => void;
  onFocus: () => void;
  onBlur: () => void;
}

const VISIBLE_LINES = 6;

export const ChatBoxView = ({ inputRef, text, lines, onTextChange, onSubmit, onFocus, onBlur }: ChatBoxViewProps) => (
  <div className="chat-box">
    <ul className="chat-lines">
      {lines.slice(-VISIBLE_LINES).map((line) => (
        <li key={line.id}>
          <strong>{line.name}:</strong> {line.text}
        </li>
      ))}
    </ul>
    <form
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      <input
        ref={inputRef}
        value={text}
        maxLength={140}
        placeholder="Press Enter to chat with people nearby"
        onChange={(event) => onTextChange(event.target.value)}
        onFocus={onFocus}
        onBlur={onBlur}
      />
    </form>
  </div>
);
