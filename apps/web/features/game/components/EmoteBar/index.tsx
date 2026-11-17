import { EMOTES } from "@park/shared";

import { sendEmote } from "@/features/game/services/connection";

const EMOTE_ICONS: Record<(typeof EMOTES)[number], string> = {
  wave: "👋",
  clap: "👏",
  laugh: "😂",
  think: "🤔",
  dance: "💃",
  heart: "❤️",
};

export const EmoteBar = () => (
  <div className="emote-bar">
    {EMOTES.map((emote) => (
      <button key={emote} type="button" title={emote} onClick={() => sendEmote(emote)}>
        {EMOTE_ICONS[emote]}
      </button>
    ))}
  </div>
);
