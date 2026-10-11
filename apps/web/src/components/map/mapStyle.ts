import type { StyleSpecification } from 'maplibre-gl';

/**
 * Minimal vector style for a self-hosted Protomaps/OSM PMTiles archive.
 * Layer names follow the Protomaps basemap schema. Attribution is mandatory:
 * the data is © OpenStreetMap contributors (ODbL).
 */
export function pmtilesStyle(pmtilesUrl: string): StyleSpecification {
  return {
    version: 8,
    glyphs: 'https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf',
    sources: {
      basemap: {
        type: 'vector',
        url: `pmtiles://${pmtilesUrl}`,
        attribution: '© OpenStreetMap contributors',
      },
    },
    layers: [
      { id: 'background', type: 'background', paint: { 'background-color': '#E7EEE4' } },
      {
        id: 'earth',
        type: 'fill',
        source: 'basemap',
        'source-layer': 'earth',
        paint: { 'fill-color': '#EEF2EA' },
      },
      {
        id: 'landuse',
        type: 'fill',
        source: 'basemap',
        'source-layer': 'landuse',
        paint: {
          'fill-color': [
            'match',
            ['get', 'kind'],
            'farmland',
            '#E6DDB8',
            'forest',
            '#CFE0C6',
            'wood',
            '#CFE0C6',
            'grass',
            '#DCE8D0',
            'residential',
            '#E4E4DF',
            'industrial',
            '#E0DEDA',
            '#E7EEE4',
          ],
        },
      },
      {
        id: 'natural',
        type: 'fill',
        source: 'basemap',
        'source-layer': 'natural',
        paint: { 'fill-color': '#D5E4CC' },
      },
      {
        id: 'water',
        type: 'fill',
        source: 'basemap',
        'source-layer': 'water',
        paint: { 'fill-color': '#9FC3E6' },
      },
      {
        id: 'roads',
        type: 'line',
        source: 'basemap',
        'source-layer': 'roads',
        paint: {
          'line-color': '#B9C3B8',
          'line-width': ['interpolate', ['linear'], ['zoom'], 8, 0.4, 14, 1.6, 18, 4],
        },
      },
      {
        id: 'boundaries',
        type: 'line',
        source: 'basemap',
        'source-layer': 'boundaries',
        paint: { 'line-color': '#8A8F98', 'line-width': 0.8, 'line-dasharray': [3, 2] },
      },
      {
        id: 'places',
        type: 'symbol',
        source: 'basemap',
        'source-layer': 'places',
        layout: {
          'text-field': ['get', 'name'],
          'text-font': ['Open Sans Regular'],
          'text-size': ['interpolate', ['linear'], ['zoom'], 4, 10, 12, 14],
        },
        paint: { 'text-color': '#3F5147', 'text-halo-color': '#FFFFFF', 'text-halo-width': 1.2 },
      },
    ],
  };
}
