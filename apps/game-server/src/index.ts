import { PARK_ROOM } from "@park/shared";
import { defineRoom, defineServer, listen } from "colyseus";

import { ParkRoom, progressStore } from "./park-room";

const PORT = Number(process.env.PORT ?? 2567);

const server = defineServer({
  rooms: {
    [PARK_ROOM]: defineRoom(ParkRoom),
  },
});

const shutdown = () => {
  progressStore.flush();
  process.exit(0);
};

process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);

listen(server, PORT).then(() => {
  console.log(`park game server listening on :${PORT}`);
});
