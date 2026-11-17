import { REPORT_REASONS } from "@park/shared";
import { useState } from "react";

import { liveState, useGameStore } from "@/features/game/hooks/use-game-store";
import { sendReport } from "@/features/game/services/connection";

export const PlayersPanel = () => {
  const playerIds = useGameStore((state) => state.playerIds);
  const selfId = useGameStore((state) => state.selfId);
  const [isOpen, setIsOpen] = useState(false);
  const others = playerIds.filter((id) => id !== selfId);

  return (
    <div className="players-panel">
      <button type="button" onClick={() => setIsOpen((value) => !value)}>
        👥 {playerIds.length} online
      </button>
      {isOpen ? (
        <ul>
          {others.length === 0 ? <li>Nobody else is here yet.</li> : null}
          {others.map((id) => (
            <li key={id}>
              <span>{liveState.players.get(id)?.name ?? id}</span>
              <select
                defaultValue=""
                onChange={(event) => {
                  const reason = REPORT_REASONS.find((item) => item === event.target.value);

                  if (reason) {
                    sendReport(id, reason);
                  }

                  event.target.value = "";
                }}
              >
                <option value="">Report…</option>
                {REPORT_REASONS.map((reason) => (
                  <option key={reason} value={reason}>
                    {reason}
                  </option>
                ))}
              </select>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
};
