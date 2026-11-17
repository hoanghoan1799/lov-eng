import { Color } from "three";

import { PALETTE_CELL_PX } from "@/features/game/constants/game";

/** Returns a darker shade of a hex colour, for the ribbing next to a recoloured cell. */
export const shadeHex = (hex: string, factor: number): string => {
  const color = new Color(hex);

  color.multiplyScalar(factor);

  return `#${color.getHexString()}`;
};

export interface CellColor {
  cell: number;
  hex: string;
}

/** Paints palette cells (one 8x8 square each, laid out in a row) onto a canvas context. */
export const paintCells = (context: Pick<CanvasRenderingContext2D, "fillStyle" | "fillRect">, cells: readonly CellColor[]) => {
  cells.forEach(({ cell, hex }) => {
    context.fillStyle = hex;
    context.fillRect(cell * PALETTE_CELL_PX, 0, PALETTE_CELL_PX, PALETTE_CELL_PX);
  });
};
