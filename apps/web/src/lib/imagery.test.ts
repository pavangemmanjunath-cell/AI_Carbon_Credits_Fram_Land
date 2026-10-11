import { describe, expect, it } from 'vitest';
import type { ImageryProvider, ImageryProvidersResponse } from '@/types/api';
import {
  availableProviders,
  chooseProvider,
  coversCountry,
  ENV_PROVIDER_ID,
  envImageryProvider,
  imageryCountry,
  resolveImagery,
  termsStatus,
} from './imagery';

function provider(id: string, extra: Partial<ImageryProvider> = {}): ImageryProvider {
  return {
    id,
    name: id,
    kind: 'xyz',
    url: `https://tiles.example/${id}/{z}/{x}/{y}.jpg`,
    tile_size: 256,
    max_zoom: 14,
    coverage: { type: 'global' },
    resolution: '10 m',
    license: 'CC BY 4.0',
    license_url: null,
    attribution: `${id} attribution`,
    requires_key: false,
    available: true,
    unavailable_reason: null,
    commercial_use: 'allowed',
    analysis_allowed: true,
    open_data: true,
    verification_status: 'verified',
    ...extra,
  };
}

const response: ImageryProvidersResponse = {
  recommended: 'eox-s2cloudless-2016',
  providers: [
    provider('ign-spain-pnoa', {
      coverage: { type: 'countries', countries: ['ES'] },
      max_zoom: 19,
    }),
    provider('eox-s2cloudless-2016'),
    provider('esri-world-imagery', {
      available: false,
      requires_key: true,
      unavailable_reason: 'ESRI_API_KEY is not set',
      analysis_allowed: false,
    }),
  ],
};

describe('imagery provider selection', () => {
  it('lists only available providers with a URL', () => {
    expect(availableProviders(response).map((p) => p.id)).toEqual([
      'ign-spain-pnoa',
      'eox-s2cloudless-2016',
    ]);
    expect(availableProviders(undefined)).toEqual([]);
  });

  it('uses the stored choice, else the recommended provider, else the first available one', () => {
    expect(chooseProvider(response)?.id).toBe('eox-s2cloudless-2016');
    expect(chooseProvider(response, 'ign-spain-pnoa')?.id).toBe('ign-spain-pnoa');
    expect(chooseProvider(response, 'esri-world-imagery')?.id).toBe('eox-s2cloudless-2016');
    expect(chooseProvider({ ...response, recommended: 'esri-world-imagery' })?.id).toBe(
      'ign-spain-pnoa',
    );
    expect(chooseProvider({ recommended: 'x', providers: [] })).toBeNull();
  });

  it('lets VITE_SATELLITE_TILES_URL override the API choice', () => {
    const resolved = resolveImagery({
      envUrl: 'https://my.tiles/{z}/{x}/{y}.png',
      envAttribution: '© Me',
      response,
      preferredId: 'ign-spain-pnoa',
    });
    expect(resolved?.id).toBe(ENV_PROVIDER_ID);
    expect(resolved?.attribution).toBe('© Me');
    expect(resolveImagery({ response })?.id).toBe('eox-s2cloudless-2016');
    expect(envImageryProvider(undefined, 'x')).toBeNull();
  });

  it('keeps the provider max zoom so MapLibre over-zooms', () => {
    expect(chooseProvider(response, 'ign-spain-pnoa')?.max_zoom).toBe(19);
    expect(chooseProvider(response)?.max_zoom).toBe(14);
  });

  it('summarises licence answers as yes / no / check the terms', () => {
    expect(termsStatus(true)).toBe('yes');
    expect(termsStatus('allowed')).toBe('yes');
    expect(termsStatus(false)).toBe('no');
    expect(termsStatus('not-allowed')).toBe('no');
    expect(termsStatus('review-terms')).toBe('check');
    expect(termsStatus(undefined)).toBe('check');
  });

  it('knows which countries a provider covers and which code to ask for', () => {
    expect(coversCountry(response.providers[0], 'es')).toBe(true);
    expect(coversCountry(response.providers[0], 'IN')).toBe(false);
    expect(coversCountry(response.providers[1], 'IN')).toBe(true);
    expect(imageryCountry('ES', 'EU')).toBe('ES');
    expect(imageryCountry(null, 'IN')).toBe('IN');
    expect(imageryCountry(undefined, 'EU')).toBeUndefined();
  });
});
