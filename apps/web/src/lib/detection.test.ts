import { describe, expect, it } from 'vitest';
import { ApiError, NetworkError } from '@/services/api';
import { FeatureNeedsApiError } from '@/services/demoFallback';
import type { Detection } from '@/types/api';
import { confidenceOpacity, detectionSummary, patchInfo } from './detection';
import { errorMessage, isAbortError, isNotFound } from './errors';

const detection: Detection = {
  detection_id: 'DET-1',
  plot_id: 'PLT-DEMOIN',
  target: 'tree-cover',
  method: 'NDVI threshold + connected components on the 10 m vegetation grid',
  index: 'ndvi',
  threshold: 0.6,
  month: '2026-09',
  features: {
    type: 'FeatureCollection',
    features: [
      {
        type: 'Feature',
        geometry: {
          type: 'Polygon',
          coordinates: [
            [
              [0, 0],
              [1, 0],
              [1, 1],
              [0, 0],
            ],
          ],
        },
        properties: {
          id: 'P1',
          label: 'tree cover',
          confidence: 0.82,
          area_m2: 4100,
          mean_ndvi: 0.71,
        },
      },
    ],
  },
  summary: { patches: 6, covered_fraction: 0.61, area_hectares: 1.3 },
  limitations: ['10 m pixels show groups of trees, not individual crowns'],
  created_at: '2026-10-05T00:00:00Z',
};

describe('AI-detected tree cover display helpers', () => {
  it('scales fill opacity with confidence', () => {
    expect(confidenceOpacity(0.5)).toBe(0.35);
    expect(confidenceOpacity(1)).toBe(0.6);
    expect(confidenceOpacity(0)).toBe(0.1);
    expect(confidenceOpacity(2)).toBe(0.6);
    expect(confidenceOpacity(null)).toBe(0.1);
    expect(confidenceOpacity(0.9)).toBeGreaterThan(confidenceOpacity(0.6));
  });

  it('summarises patches and covered share from the server', () => {
    expect(detectionSummary(detection)).toEqual({
      patches: 6,
      coveredFraction: 0.61,
      areaHectares: 1.3,
    });
    expect(detectionSummary(undefined)).toBeNull();
  });

  it('prepares the popup values for one patch', () => {
    expect(patchInfo(detection.features.features[0].properties)).toEqual({
      confidence: '0.82',
      hectares: 0.41,
    });
    expect(patchInfo({ confidence: 0.5 })).toBeNull();
    expect(patchInfo(undefined)).toBeNull();
  });
});

describe('error messages', () => {
  const t = (key: string, options?: Record<string, unknown>) =>
    options ? `${key}:${JSON.stringify(options)}` : key;

  it('shows the RFC 7807 detail of API problems', () => {
    expect(
      errorMessage(
        new ApiError(
          415,
          {
            title: 'Unsupported Media Type',
            detail: 'Convert the E57 file to LAS/LAZ with CloudCompare or PDAL.',
          },
          'x',
        ),
        t,
      ),
    ).toBe('Convert the E57 file to LAS/LAZ with CloudCompare or PDAL.');
    expect(errorMessage(new ApiError(413, { title: 'Payload Too Large' }, 'x'), t)).toBe(
      'Payload Too Large',
    );
  });

  it('uses friendly messages for server-only features, network failures and cancels', () => {
    expect(errorMessage(new FeatureNeedsApiError('Importing files'), t)).toBe('errors.needsApi');
    expect(errorMessage(new NetworkError('down'), t)).toBe('errors.network');
    expect(errorMessage(new DOMException('stop', 'AbortError'), t)).toBe('errors.cancelled');
    expect(errorMessage({}, t)).toBe('errors.unknown');
    expect(errorMessage(null, t)).toBe('');
    expect(isAbortError(new DOMException('stop', 'AbortError'))).toBe(true);
    expect(isNotFound(new ApiError(404, undefined, 'x'))).toBe(true);
  });
});
