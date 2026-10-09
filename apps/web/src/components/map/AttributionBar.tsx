import { useEffect, useMemo, useState } from 'react';
import { Info } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { Map as MapLibreMap } from 'maplibre-gl';
import { attributionParts, dataAttributions, styleAttributions } from '@/lib/attribution';
import { formatLatLon } from '@/lib/coordinates';
import { metresPerPixel, scaleBarSpec, type ScaleBarSpec } from '@/lib/scale';
import type { LatLon } from '@/types/api';

/** Metric scale bar that follows the map's zoom and latitude. */
export function ScaleBar({ map, maxWidthPx = 96 }: { map: MapLibreMap | null; maxWidthPx?: number }) {
  const { t } = useTranslation();
  const [spec, setSpec] = useState<ScaleBarSpec | null>(null);

  useEffect(() => {
    if (!map) return;
    let frame = 0;
    const update = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        const center = map.getCenter();
        setSpec(scaleBarSpec(metresPerPixel(center.lat, map.getZoom()), maxWidthPx));
      });
    };
    update();
    map.on('move', update);
    map.on('resize', update);
    return () => {
      cancelAnimationFrame(frame);
      map.off('move', update);
      map.off('resize', update);
    };
  }, [map, maxWidthPx]);

  if (!spec || spec.widthPx <= 0) return null;
  return (
    <span role="img" aria-label={t('map.scaleLabel', { distance: spec.label })} className="flex shrink-0 items-end gap-1.5">
      <span
        aria-hidden="true"
        className="block h-[7px] border-x-2 border-b-2 border-ink-2"
        style={{ width: `${spec.widthPx}px` }}
      />
      <span className="font-mono text-[11px] leading-none text-ink-2">{spec.label}</span>
    </span>
  );
}

interface AttributionBarProps {
  map: MapLibreMap | null;
  ready: boolean;
  /** Attribution of the active satellite imagery (only while the Satellite view is on). */
  imageryAttribution?: string | null;
  basemapFallback: boolean;
  imageryFailed: boolean;
  centroid?: LatLon | null;
}

/** Our own attribution bar (replaces MapLibre's controls): scale bar · licences · plot centre. */
export function AttributionBar({ map, ready, imageryAttribution, basemapFallback, imageryFailed, centroid }: AttributionBarProps) {
  const { t } = useTranslation();
  const [basemap, setBasemap] = useState<string[]>([]);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    if (!map || !ready) return;
    const update = () => {
      const next = styleAttributions(map.getStyle());
      setBasemap((prev) => (prev.join('|') === next.join('|') ? prev : next));
    };
    update();
    // Basemap sources arrive with the style; tile loads (`sourcedata`) never change attribution.
    map.on('styledata', update);
    return () => {
      map.off('styledata', update);
    };
  }, [map, ready]);

  const parts = useMemo(() => attributionParts({ basemap, imagery: imageryAttribution, data: dataAttributions() }), [basemap, imageryAttribution]);

  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-line bg-surface px-3 py-1.5 text-[11px] text-ink-2">
      <ScaleBar map={ready ? map : null} />
      {basemapFallback && (
        <span role="status" className="rounded-full bg-amber-tint px-2 py-0.5 font-medium text-amber-text">
          {t('map.basemapUnavailable')}
        </span>
      )}
      {imageryFailed && (
        <span role="status" className="rounded-full bg-amber-tint px-2 py-0.5 font-medium text-amber-text">
          {t('map.imageryFailed')}
        </span>
      )}
      <span className="flex min-w-0 flex-[1_1_360px] items-start gap-1.5">
        <span className={`min-w-0 flex-1 ${expanded ? '' : 'line-clamp-1 md:line-clamp-2'}`} title={parts.join(' · ')}>
          <span className="sr-only">{t('map.attributionLabel')}: </span>
          {parts.join(' · ')}
        </span>
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          aria-expanded={expanded}
          aria-label={t('map.attributionToggle')}
          className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-muted hover:bg-ground"
        >
          <Info size={13} aria-hidden="true" />
        </button>
      </span>
      {centroid && <span className="hidden shrink-0 font-mono sm:inline">{formatLatLon(centroid)}</span>}
    </div>
  );
}
