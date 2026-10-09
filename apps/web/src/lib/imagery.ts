/**
 * Satellite / aerial imagery selection for the map's "Satellite" view.
 * Providers, licences and the per-country recommendation come from
 * `GET /imagery/providers` (config/imagery/providers.yaml); the deployer can
 * still force a tile URL with VITE_SATELLITE_TILES_URL.
 */
import type { ImageryProvider, ImageryProvidersResponse, TermsAnswer } from '@/types/api';

export const ENV_PROVIDER_ID = 'env-override';

/** Provider built from VITE_SATELLITE_TILES_URL / VITE_SATELLITE_ATTRIBUTION. */
export function envImageryProvider(url: string | undefined, attribution: string | undefined): ImageryProvider | null {
  if (!url) return null;
  return {
    id: ENV_PROVIDER_ID,
    name: 'Configured imagery (VITE_SATELLITE_TILES_URL)',
    kind: 'xyz',
    url,
    tile_size: 256,
    max_zoom: 19,
    coverage: { type: 'global' },
    resolution: '',
    license: 'Set by the deployer',
    license_url: null,
    attribution: attribution ?? '',
    requires_key: false,
    available: true,
    unavailable_reason: null,
    commercial_use: 'review-terms',
    analysis_allowed: 'review-terms',
    open_data: false,
    verification_status: 'assumption',
  };
}

export function availableProviders(response: ImageryProvidersResponse | null | undefined): ImageryProvider[] {
  return (response?.providers ?? []).filter((p) => p.available && Boolean(p.url));
}

/** The user's stored choice when still available, else the recommended provider, else the first available one. */
export function chooseProvider(response: ImageryProvidersResponse | null | undefined, preferredId?: string | null): ImageryProvider | null {
  const available = availableProviders(response);
  if (available.length === 0) return null;
  return (
    (preferredId ? available.find((p) => p.id === preferredId) : undefined) ??
    available.find((p) => p.id === response?.recommended) ??
    available[0]
  );
}

export function resolveImagery(input: {
  envUrl?: string;
  envAttribution?: string;
  response?: ImageryProvidersResponse | null;
  preferredId?: string | null;
}): ImageryProvider | null {
  return envImageryProvider(input.envUrl, input.envAttribution) ?? chooseProvider(input.response, input.preferredId);
}

export type TermsStatus = 'yes' | 'no' | 'check';

/** `true`/`allowed` → yes · `false`/`not-allowed` → no · anything else (e.g. `review-terms`) → check the terms. */
export function termsStatus(answer: TermsAnswer | null | undefined): TermsStatus {
  if (answer === true || answer === 'allowed') return 'yes';
  if (answer === false || answer === 'not-allowed') return 'no';
  return 'check';
}

export function coversCountry(provider: ImageryProvider, country: string | null | undefined): boolean {
  if (provider.coverage.type === 'global') return true;
  return Boolean(country) && provider.coverage.countries.includes(String(country).toUpperCase());
}

/** Country code sent to `GET /imagery/providers`: the plot's ISO code, else the app country (EU → none, the server default applies). */
export function imageryCountry(plotCountry: string | null | undefined, appCountry: string | null | undefined): string | undefined {
  const code = (plotCountry ?? appCountry ?? '').toUpperCase();
  return code && code !== 'EU' ? code : undefined;
}
