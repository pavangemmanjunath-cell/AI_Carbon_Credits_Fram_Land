/**
 * Map-related VITE_* variables, read once. Endpoints come from the
 * environment — never literals in components (CLAUDE.md rule 6).
 */
function env(name: string): string | undefined {
  const value = (import.meta.env[name] as string | undefined)?.trim();
  return value && value.length > 0 ? value : undefined;
}

export const DEFAULT_BASEMAP_STYLE_URL = 'https://tiles.openfreemap.org/styles/liberty';

export const mapEnv = {
  basemapStyleUrl: env('VITE_BASEMAP_STYLE_URL') ?? DEFAULT_BASEMAP_STYLE_URL,
  basemapPmtilesUrl: env('VITE_BASEMAP_PMTILES_URL'),
  satelliteTilesUrl: env('VITE_SATELLITE_TILES_URL'),
  satelliteAttribution: env('VITE_SATELLITE_ATTRIBUTION') ?? '',
  defaultCountry: env('VITE_DEFAULT_COUNTRY') ?? 'IN',
  defaultLanguage: env('VITE_DEFAULT_LANGUAGE') ?? 'en',
} as const;

/** VITE_SATELLITE_TILES_URL overrides the imagery provider chosen through the API. */
export const hasSatelliteOverride = Boolean(mapEnv.satelliteTilesUrl);
