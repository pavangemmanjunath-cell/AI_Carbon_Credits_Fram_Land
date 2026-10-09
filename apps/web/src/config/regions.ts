import regionsJson from './regions.json';

export type AreaUnit = 'hectare' | 'acre';

export interface UiRegion {
  id: string;
  name: string;
  calling_code: string | null;
  currency: string;
  currency_symbol: string;
  locale: string;
  units: { area: AreaUnit; area_secondary: AreaUnit };
  languages: string[];
  default_center: { lat: number; lon: number };
  default_zoom: number;
  bbox: [number, number, number, number];
  climate: { default_zone: string };
  programmes: { id: string; name: string; authority: string; kind: string; url: string }[];
  other_income_sources: { id: string; label: string; source: string }[];
}

export const REGIONS: UiRegion[] = regionsJson.regions as UiRegion[];
export const EU_MEMBER_STATES: string[] = regionsJson.eu_member_states;
export const REGION_IDS = REGIONS.map((r) => r.id);

/** Maps any ISO code to the rule region (EU member states resolve to `EU`). */
export function regionIdFor(country: string | undefined | null): string {
  if (!country) return 'IN';
  const upper = country.toUpperCase();
  if (REGION_IDS.includes(upper)) return upper;
  if (EU_MEMBER_STATES.includes(upper)) return 'EU';
  return 'IN';
}

export function regionFor(country: string | undefined | null): UiRegion {
  const id = regionIdFor(country);
  return REGIONS.find((r) => r.id === id) ?? REGIONS[0];
}
