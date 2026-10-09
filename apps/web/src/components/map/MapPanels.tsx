import { Layers, Search } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useDebouncedValue } from '@/hooks/useDebouncedValue';
import type { DetectionSummary } from '@/lib/detection';
import type { LandUseShare, SoilInsight } from '@/lib/insights';
import { errorMessage } from '@/lib/errors';
import { formatInteger, formatNumber, formatPercent } from '@/lib/format';
import { useGeocode } from '@/services/queries';
import { useUiStore, type LayerKey } from '@/store/uiStore';
import type { GeocodeResult } from '@/types/api';

// ─── Search ─────────────────────────────────────────────────────────────────
export function MapSearch({ country, onPick, initialQuery = '' }: { country: string; onPick: (r: GeocodeResult) => void; initialQuery?: string }) {
  const { t } = useTranslation();
  const [query, setQuery] = useState(initialQuery);
  const [open, setOpen] = useState(false);
  const debounced = useDebouncedValue(query, 350);
  const { data, isFetching } = useGeocode(debounced, country === 'EU' ? undefined : country);
  const wrapper = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (wrapper.current && !wrapper.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, []);

  const results = data?.results ?? [];
  return (
    <div ref={wrapper} className="relative w-[min(440px,calc(100vw-120px))]">
      <form
        role="search"
        className="float-control flex h-11 items-center gap-2.5 px-3.5"
        onSubmit={(e) => {
          e.preventDefault();
          if (results[0]) {
            onPick(results[0]);
            setOpen(false);
          }
        }}
      >
        <Search size={18} className="shrink-0 text-muted" aria-hidden="true" />
        <input
          type="search"
          aria-label={t('map.searchLabel')}
          placeholder={t('map.searchPlaceholder')}
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          className="h-full w-full bg-transparent text-sm outline-none placeholder:text-muted"
        />
        {isFetching && <span className="h-4 w-4 animate-spin rounded-full border-2 border-line border-t-forest" aria-hidden="true" />}
      </form>
      {open && debounced.trim().length >= 3 && (
        <ul role="listbox" className="float-control absolute left-0 right-0 top-12 z-20 max-h-64 overflow-auto py-1 text-sm">
          {results.length === 0 && !isFetching && <li className="px-3.5 py-2 text-muted">{t('map.noResults')}</li>}
          {results.map((r) => (
            <li key={`${r.lat}-${r.lon}-${r.label}`}>
              <button
                type="button"
                className="flex w-full flex-col items-start px-3.5 py-2 text-left hover:bg-ground"
                onClick={() => {
                  onPick(r);
                  setQuery(r.label);
                  setOpen(false);
                }}
              >
                <span className="text-ink">{r.label}</span>
                <span className="font-mono text-[11px] text-muted">
                  {r.lat.toFixed(4)}, {r.lon.toFixed(4)}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ─── Layer panel ─────────────────────────────────────────────────────────────
const LAYER_ITEMS: { key: LayerKey; label: string; hint: string }[] = [
  { key: 'landuse', label: 'map.layerLanduse', hint: 'map.layerLanduseHint' },
  { key: 'ndvi', label: 'map.layerNdvi', hint: 'map.layerNdviHint' },
  { key: 'soil', label: 'map.layerSoil', hint: 'map.layerSoilHint' },
  { key: 'treeCover', label: 'map.layerTreeCover', hint: 'map.layerTreeCoverHint' },
  { key: 'importedTrees', label: 'map.layerImportedTrees', hint: 'map.layerImportedTreesHint' },
];

export interface TreeCoverStatus {
  summary: DetectionSummary | null;
  loading: boolean;
  error: unknown;
}

export interface ImportedTreesStatus {
  count: number | null;
  filename: string | null;
  loading: boolean;
  error: unknown;
}

/** Plot-level insights shown under the "Land use" and "Soil & terrain" toggles. */
export interface PlotInsights {
  landUse: LandUseShare[];
  soil: SoilInsight | null;
  loading: boolean;
}

interface LayerPanelProps {
  hasPlot: boolean;
  locale: string;
  treeCover: TreeCoverStatus;
  importedTrees: ImportedTreesStatus;
  insights: PlotInsights;
  /** The basemap legend; hidden over satellite imagery, where its colours do not apply. */
  showLegend?: boolean;
}

export function LayerPanel({ hasPlot, locale, treeCover, importedTrees, insights, showLegend = true }: LayerPanelProps) {
  const { t } = useTranslation();
  const layers = useUiStore((s) => s.layers);
  const toggleLayer = useUiStore((s) => s.toggleLayer);
  const on = Object.values(layers).filter(Boolean).length;

  const detail = (key: LayerKey) => {
    if (!layers[key]) return null;
    if (key === 'landuse' || key === 'soil') {
      if (!hasPlot) return <span className="text-muted">{t('map.selectPlotFirst')}</span>;
      if (insights.loading) return <span className="text-muted">{t('app.loading')}</span>;
      if (key === 'landuse') {
        if (!insights.landUse.length) return <span className="text-muted">{t('map.landUseNone')}</span>;
        return (
          <span className="font-medium text-forest-deep">
            {insights.landUse.map((c) => `${formatPercent(c.share, locale)} ${c.key ? t(c.key) : c.name}`).join(' · ')}
          </span>
        );
      }
      const soil = insights.soil;
      if (!soil) return <span className="text-muted">{t('map.soilNone')}</span>;
      return (
        <>
          {soil.socGPerKg != null && (
            <span className="font-medium text-forest-deep">{t('map.soilSummary', { soc: formatNumber(soil.socGPerKg, locale, { maximumFractionDigits: 1 }) })}</span>
          )}
          {soil.climateZoneLabel && <span className="text-muted">{t('map.climateZoneLine', { zone: soil.climateZoneLabel })}</span>}
        </>
      );
    }
    if (key === 'treeCover') {
      if (!hasPlot) return <span className="text-muted">{t('map.selectPlotFirst')}</span>;
      if (treeCover.loading) return <span className="text-muted">{t('map.treeCoverLoading')}</span>;
      if (treeCover.error) return <span className="text-amber-text">{errorMessage(treeCover.error, t)}</span>;
      return (
        <>
          {treeCover.summary && (
            <span className="font-medium text-forest-deep">
              {t('map.treeCoverSummary', { count: treeCover.summary.patches, n: formatInteger(treeCover.summary.patches, locale), share: formatPercent(treeCover.summary.coveredFraction, locale) })}
            </span>
          )}
          <span className="text-muted">{t('map.treeCoverNote')}</span>
        </>
      );
    }
    if (key === 'importedTrees') {
      if (importedTrees.loading) return <span className="text-muted">{t('app.loading')}</span>;
      if (importedTrees.error) return <span className="text-amber-text">{errorMessage(importedTrees.error, t)}</span>;
      if (importedTrees.count == null) return <span className="text-muted">{t('map.importedTreesNone')}</span>;
      return (
        <span className="font-medium text-forest-deep">
          {t('map.importedTreesCount', { count: importedTrees.count, n: formatInteger(importedTrees.count, locale), file: importedTrees.filename ?? '' })}
        </span>
      );
    }
    return null;
  };

  return (
    <section aria-label={t('map.layersTitle')} className="float-control flex min-h-0 w-[272px] flex-col gap-2 overflow-y-auto p-3">
      <div className="flex items-center justify-between">
        <span className="flex items-center gap-2 text-[13px] font-semibold">
          <Layers size={16} className="text-forest" aria-hidden="true" />
          {t('map.layersTitle')}
        </span>
        <span className="font-mono text-[11px] text-muted">{t('map.layersOn', { count: on })}</span>
      </div>
      {LAYER_ITEMS.map((item) => {
        const extra = detail(item.key);
        return (
          <label key={item.key} className="flex cursor-pointer items-start gap-2.5 text-[13px]">
            <input type="checkbox" className="mt-0.5 h-[18px] w-[18px] shrink-0 accent-forest" checked={layers[item.key]} onChange={() => toggleLayer(item.key)} />
            <span className="flex min-w-0 flex-col">
              <span className="font-medium">{t(item.label)}</span>
              <span className="text-[11px] text-muted">{t(item.hint)}</span>
              {extra && <span className="mt-0.5 flex flex-col gap-0.5 text-[11px] leading-snug">{extra}</span>}
            </span>
          </label>
        );
      })}
      {showLegend && <Legend />}
    </section>
  );
}

// ─── Year slider ─────────────────────────────────────────────────────────────
export function YearSlider({ years, value, onChange, caption }: { years: number[]; value: number; onChange: (y: number) => void; caption: string }) {
  const { t } = useTranslation();
  if (years.length === 0) return null;
  const min = years[0];
  const max = years[years.length - 1];
  return (
    <section aria-label={t('map.observationYear')} className="float-control flex w-full max-w-[340px] flex-col gap-1.5 px-3.5 py-2.5">
      <div className="flex items-center justify-between text-[12px]">
        <label htmlFor="observation-year" className="font-semibold">
          {t('map.observationYear')}
        </label>
        <span className="font-mono text-ink-2">{caption}</span>
      </div>
      <input id="observation-year" type="range" min={min} max={max} step={1} value={value} onChange={(e) => onChange(Number(e.target.value))} className="range-input" />
      <div className="flex justify-between font-mono text-[11px] text-muted">
        {years.map((y) => (
          <span key={y}>{y}</span>
        ))}
      </div>
    </section>
  );
}

// ─── Legend (bottom of the layer panel) ─────────────────────────────────────
export function Legend() {
  const { t } = useTranslation();
  const rows = [
    { label: t('map.legendPlantation'), swatch: 'bg-plot-fill border-2 border-forest' },
    { label: t('map.legendCultivated'), swatch: 'bg-[#D9CBA3]' },
    { label: t('map.legendOther'), swatch: 'bg-[#CFE0C6]' },
    { label: t('map.legendWater'), swatch: 'bg-[#7FB1E0]' },
  ];
  return (
    <section aria-label={t('map.legendTitle')} className="mt-1 grid grid-cols-2 gap-x-3 gap-y-1.5 border-t border-line pt-2.5 text-[12px]">
      {rows.map((r) => (
        <span key={r.label} className="flex items-center gap-2">
          <span className={`h-3.5 w-3.5 rounded-[3px] ${r.swatch}`} aria-hidden="true" />
          {r.label}
        </span>
      ))}
    </section>
  );
}
