/**
 * Layout for the Simulation page's stand illustration: a few rows of simple
 * tree glyphs whose size follows the stand's age. Purely visual — the carbon
 * numbers on the page come from the simulation engine, never from this.
 */

export interface TreeGlyph {
  /** Centre of the trunk base, in SVG units. */
  x: number;
  y: number;
  /** 0–1 size factor (growth × depth of the row). */
  scale: number;
  row: number;
}

export interface StandLayout {
  glyphs: TreeGlyph[];
  /** How many real trees one glyph stands for (1 when every tree is drawn). */
  treesPerGlyph: number;
  width: number;
  height: number;
  /** y of the horizon line (top of the ground). */
  horizon: number;
}

export const MAX_GLYPHS = 60;
export const MAX_ROWS = 5;

interface Options {
  width?: number;
  height?: number;
  maxGlyphs?: number;
}

/** Rows from back (small, high) to front (large, low); alternate rows are offset like an orchard. */
export function standLayout(treeCount: number, growth: number, options: Options = {}): StandLayout {
  const width = options.width ?? 640;
  const height = options.height ?? 320;
  const maxGlyphs = options.maxGlyphs ?? MAX_GLYPHS;
  const horizon = Math.round(height * 0.36);
  const count = Math.max(0, Math.round(treeCount));
  const shown = Math.min(count, maxGlyphs);
  if (shown === 0) return { glyphs: [], treesPerGlyph: 1, width, height, horizon };
  const rows = Math.min(MAX_ROWS, Math.max(1, Math.ceil(Math.sqrt(shown / 3))));
  const perRow = Math.ceil(shown / rows);
  const g = Math.max(0, Math.min(1, growth));
  const glyphs: TreeGlyph[] = [];
  for (let row = 0; row < rows; row += 1) {
    const inRow = Math.min(perRow, shown - row * perRow);
    if (inRow <= 0) break;
    const depth = rows === 1 ? 1 : 0.62 + (0.38 * row) / (rows - 1);
    const y = horizon + 26 + ((height - horizon - 40) * (row + 1)) / rows;
    const margin = 36 * depth;
    const span = width - margin * 2;
    const step = span / inRow;
    const offset = row % 2 === 1 ? step / 2 : 0;
    for (let i = 0; i < inRow; i += 1) {
      const x = margin + step * i + step / 2 + offset - (row % 2 === 1 ? step / 4 : 0);
      glyphs.push({
        x: Number(x.toFixed(1)),
        y: Number(y.toFixed(1)),
        scale: Number((g * depth).toFixed(3)),
        row,
      });
    }
  }
  return {
    glyphs,
    treesPerGlyph: count > shown ? Math.round(count / shown) : 1,
    width,
    height,
    horizon,
  };
}
