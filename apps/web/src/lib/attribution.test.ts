import { describe, expect, it } from 'vitest';
import { attributionParts, dataAttributions, plainAttribution, styleAttributions } from './attribution';

describe('map attribution', () => {
  it('turns HTML attribution into plain text', () => {
    expect(plainAttribution('<a href="https://www.openstreetmap.org/copyright">&copy; OpenStreetMap</a> contributors')).toBe('© OpenStreetMap contributors');
    expect(plainAttribution('<script>alert(1)</script>Esri &amp; partners')).toBe('alert(1) Esri & partners');
    expect(plainAttribution(null)).toBe('');
  });

  it('reads basemap attribution from the style, skipping our own atlas- sources', () => {
    const style = {
      sources: {
        openmaptiles: { attribution: '© OpenStreetMap contributors' },
        'atlas-imagery': { attribution: 'Imagery credit' },
        'td-polygon': {},
      },
    };
    expect(styleAttributions(style)).toEqual(['© OpenStreetMap contributors']);
    expect(styleAttributions(undefined)).toEqual([]);
  });

  it('orders basemap, imagery, data layers and drops duplicates', () => {
    const parts = attributionParts({
      basemap: ['© OpenStreetMap contributors', '© OpenStreetMap contributors'],
      imagery: 'EOxCloudless https://cloudless.eox.at by EOX IT Services GmbH',
      data: dataAttributions(2026),
    });
    expect(parts).toEqual([
      '© OpenStreetMap contributors',
      'EOxCloudless https://cloudless.eox.at by EOX IT Services GmbH',
      'ESA WorldCover 2021 © ESA (CC BY 4.0)',
      'Contains modified Copernicus Sentinel data 2026',
    ]);
    expect(attributionParts({ basemap: [], imagery: null, data: [] })).toEqual([]);
  });
});
