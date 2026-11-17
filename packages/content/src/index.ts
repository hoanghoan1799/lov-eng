import { type Mission, missionSchema, pathFileSchema } from "@park/shared";

import coffeeOrderDrink from "../missions/coffee-order-drink.json";
import parkGreeting from "../missions/park-greeting.json";
import restaurantBookTable from "../missions/restaurant-book-table.json";
import supermarketFindItem from "../missions/supermarket-find-item.json";
import pathJson from "../path.json";
import colliders from "../world/island_colliders.json";
import heightmap from "../world/island_height.json";
import layout from "../world/island_layout.json";

export const PATH = pathFileSchema.parse(pathJson);

const MISSION_LIST: Mission[] = [parkGreeting, coffeeOrderDrink, restaurantBookTable, supermarketFindItem].map((mission) =>
  missionSchema.parse(mission),
);

export const MISSIONS: Record<string, Mission> = Object.fromEntries(MISSION_LIST.map((mission) => [mission.id, mission]));

/** Island data exported from Blender (game coordinates: x east, z south, y up). */
export const WORLD_COLLIDERS = colliders as { boxes: [number, number, number, number, number, string][]; obbs: [number, number, number, number, number, number, number, string][]; circles: [number, number, number][] };
export const WORLD_HEIGHTMAP = heightmap as { size: number; step: number; origin: number; heights: number[][] };
export const WORLD_LAYOUT = layout;
