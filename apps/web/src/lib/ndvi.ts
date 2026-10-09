import type { NdviClass } from '@/types/api';

/** Discrete NDVI palette — 8 classes. Upper bounds are exclusive except the last. */
export const NDVI_CLASSES: { upper: number; hex: string }[] = [
  { upper: 0.2, hex: '#8C5A2B' },
  { upper: 0.3, hex: '#B98A3A' },
  { upper: 0.4, hex: '#D9C14C' },
  { upper: 0.5, hex: '#C9D45A' },
  { upper: 0.6, hex: '#A9CF5A' },
  { upper: 0.7, hex: '#6EBE63' },
  { upper: 0.8, hex: '#3C9E58' },
  { upper: Number.POSITIVE_INFINITY, hex: '#1E6B41' },
];

export const NDVI_NULL_HEX = '#D8E0DA';

export function ndviClassIndex(value: number): number {
  for (let i = 0; i < NDVI_CLASSES.length; i += 1) {
    if (value < NDVI_CLASSES[i].upper) return i;
  }
  return NDVI_CLASSES.length - 1;
}

export function ndviColor(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return NDVI_NULL_HEX;
  return NDVI_CLASSES[ndviClassIndex(value)].hex;
}

export function hexToRgb(hex: string): [number, number, number] {
  const clean = hex.replace('#', '');
  const n = parseInt(clean, 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

export function ndviColorRgb(value: number | null | undefined): [number, number, number] {
  return hexToRgb(ndviColor(value));
}

/** Contract classes: sparse < 0.3, moderate 0.3–0.6, healthy ≥ 0.6. */
export function ndviClass(value: number): NdviClass {
  if (value < 0.3) return 'sparse';
  if (value < 0.6) return 'moderate';
  return 'healthy';
}

/** Legend labels for the discrete scale. */
export function ndviLegend(): { label: string; hex: string }[] {
  return NDVI_CLASSES.map((c, i) => {
    const lower = i === 0 ? null : NDVI_CLASSES[i - 1].upper;
    const label =
      lower === null
        ? `< ${c.upper.toFixed(1)}`
        : Number.isFinite(c.upper)
          ? `${lower.toFixed(1)}–${c.upper.toFixed(1)}`
          : `≥ ${lower.toFixed(1)}`;
    return { label, hex: c.hex };
  });
}
