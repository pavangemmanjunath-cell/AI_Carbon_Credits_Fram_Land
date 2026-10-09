/** ESA WorldCover class codes → display colour and i18n key. */
export interface LandcoverStyle {
  code: number;
  key: string;
  hex: string;
}

export const LANDCOVER_STYLES: LandcoverStyle[] = [
  { code: 10, key: 'landcover.tree_cover', hex: '#2E8B57' },
  { code: 20, key: 'landcover.shrubland', hex: '#B4A24A' },
  { code: 30, key: 'landcover.grassland', hex: '#A9C96A' },
  { code: 40, key: 'landcover.cropland', hex: '#D9A441' },
  { code: 50, key: 'landcover.built_up', hex: '#8A8F98' },
  { code: 60, key: 'landcover.bare', hex: '#C9B99B' },
  { code: 80, key: 'landcover.water', hex: '#2A6FB0' },
  { code: 90, key: 'landcover.wetland', hex: '#5BA3A0' },
  { code: 95, key: 'landcover.wetland', hex: '#5BA3A0' },
];

const BY_NAME: Record<string, string> = {
  'tree cover': '#2E8B57',
  shrubland: '#B4A24A',
  grassland: '#A9C96A',
  cropland: '#D9A441',
  'built-up': '#8A8F98',
  'bare / sparse vegetation': '#C9B99B',
  bare: '#C9B99B',
  'permanent water bodies': '#2A6FB0',
  water: '#2A6FB0',
  'herbaceous wetland': '#5BA3A0',
  wetland: '#5BA3A0',
  mangroves: '#5BA3A0',
};

export function landcoverColor(code: number | undefined, name?: string): string {
  const byCode = LANDCOVER_STYLES.find((s) => s.code === code);
  if (byCode) return byCode.hex;
  if (name) {
    const hit = BY_NAME[name.toLowerCase()];
    if (hit) return hit;
  }
  return '#C9B99B';
}
