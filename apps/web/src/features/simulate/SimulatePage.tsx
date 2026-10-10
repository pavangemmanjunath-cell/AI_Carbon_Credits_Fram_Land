import { lazy, Suspense, useEffect, useMemo, useState } from 'react';
import { ExternalLink, Link2, Pause, Play } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Link, useSearchParams } from 'react-router';
import { Button } from '@/components/ui/Button';
import { REGIONS, regionIdFor } from '@/config/regions';
import { useDebouncedValue } from '@/hooks/useDebouncedValue';
import { copyToClipboard } from '@/lib/download';
import { formatCurrency, formatNumber, formatRange, intlLocale, unitLabel } from '@/lib/format';
import { usePlot, useSimulation, useSpecies } from '@/services/queries';
import { useUiStore } from '@/store/uiStore';
import { growthFactor, parseSimulationParams, shareUrl, toSearchParams, toSimulateBody, type SimulationState } from './logic/simulationParams';
import { MAX_GLYPHS } from './logic/standIllustration';
import { StandIllustration } from './StandIllustration';
import { CostPanel } from './land3d/CostPanel';
import { EMPTY_COSTS, toCostInputs, type CostDraft } from './land3d/costs';
import { CreditPathway } from './land3d/CreditPathway';
import { ExplainPanel } from './land3d/ExplainPanel';
import { carbonInYear, projectRing, squareRing } from './land3d/landScene';
import { hasWebGL } from './land3d/webgl';
import './land3d/i18n';

const LandView3D = lazy(() => import('./land3d/LandView3D'));

export default function SimulatePage() {
  const { t } = useTranslation();
  const [params, setParams] = useSearchParams();
  const language = useUiStore((s) => s.language);
  const storeCountry = useUiStore((s) => s.country);
  const selectedPlotId = useUiStore((s) => s.selectedPlotId);

  const [initial] = useState(() =>
    parseSimulationParams(params, { country: storeCountry, species: 'mango', trees: 420, year: new Date().getFullYear() - 3, horizon: 30, area: 2.13, plot: selectedPlotId }),
  );
  const [state, setState] = useState<SimulationState>(initial);
  const [standYear, setStandYear] = useState<number>(new Date().getFullYear());
  const [playing, setPlaying] = useState(false);
  const [copied, setCopied] = useState(false);
  const [webgl] = useState(hasWebGL);
  const [view, setView] = useState<'3d' | '2d'>(() => (hasWebGL() ? '3d' : '2d'));
  const [costDraft, setCostDraft] = useState<CostDraft>(EMPTY_COSTS);

  const regionId = regionIdFor(state.country);
  const species = useSpecies(regionId).data ?? [];
  const plot = usePlot(state.plot).data;

  // Keep species valid for the region and sync the URL (source of truth for sharing).
  useEffect(() => {
    if (species.length && !species.some((s) => s.id === state.species)) setState((s) => ({ ...s, species: species[0].id }));
  }, [species, state.species]);
  useEffect(() => {
    if (plot && plot.area_hectares !== state.area) setState((s) => ({ ...s, area: plot.area_hectares }));
  }, [plot, state.area]);
  useEffect(() => {
    const next = toSearchParams(state);
    if (next.toString() !== params.toString()) setParams(next, { replace: true });
  }, [state, params, setParams]);

  const debounced = useDebouncedValue(state, 300);
  const debouncedCosts = useDebouncedValue(costDraft, 500);
  const baseBody = toSimulateBody(debounced);
  const costs = toCostInputs(debouncedCosts);
  const simulation = useSimulation(baseBody && costs ? { ...baseBody, costs } : baseBody).data;
  const locale = intlLocale(language, state.country);

  // Stand-year scrubber
  const horizonEnd = state.year + state.horizon;
  useEffect(() => {
    setStandYear((y) => Math.min(Math.max(y, state.year), horizonEnd));
  }, [state.year, horizonEnd]);
  useEffect(() => {
    if (!playing) return;
    const timer = window.setInterval(() => setStandYear((y) => (y >= horizonEnd ? state.year : y + 1)), 350);
    return () => window.clearInterval(timer);
  }, [playing, horizonEnd, state.year]);

  const speciesEntry = species.find((s) => s.id === state.species);
  const maturity = speciesEntry?.maturity_years ?? 10;
  const age = Math.max(0, standYear - state.year);
  const growth = growthFactor(age, maturity);
  // Canopy colour only (illustration), never displayed as an index value.
  const canopyTone = 0.35 + growth * 0.45;

  const copyLink = async () => {
    setCopied(await copyToClipboard(shareUrl(state)));
    setTimeout(() => setCopied(false), 2000);
  };
  const region = REGIONS.find((r) => r.id === regionId);
  // The saved boundary is projected here in the browser and never sent anywhere.
  const ring = useMemo(() => {
    const projected = plot?.geometry ? projectRing(plot.geometry) : [];
    return projected.length >= 3 ? projected : squareRing(state.area);
  }, [plot?.geometry, state.area]);
  const yearCarbon = simulation ? carbonInYear(simulation.series, standYear, state.trees) : null;
  const activeProgramme = simulation?.programmes[0];

  return (
    <div className="flex flex-col gap-4 p-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="flex max-w-[760px] flex-col gap-1">
          <nav aria-label="Breadcrumb" className="flex items-center gap-2 text-[13px] text-muted">
            <Link to="/app" className="text-ink-2 no-underline hover:text-forest">{t('results.breadcrumbWorkspace')}</Link>
            <span aria-hidden="true">›</span>
            <span className="font-semibold text-ink">{t('nav.simulation')}</span>
          </nav>
          <h1 className="m-0 text-[28px] tracking-tight">{t('simulate.title')}</h1>
          <p className="m-0 text-sm text-ink-2">{t('simulate.subtitle')}</p>
        </div>
        <div role="group" aria-label={t('settings.country')} className="card flex gap-1 p-1">
          {REGIONS.map((r) => (
            <button
              key={r.id}
              type="button"
              aria-pressed={regionId === r.id}
              onClick={() => setState((s) => ({ ...s, country: r.id }))}
              className={`h-9 rounded-[7px] px-3.5 text-[13px] font-semibold ${regionId === r.id ? 'bg-panel-dark text-white' : 'text-ink-2 hover:bg-ground'}`}
            >
              {t(`country.${r.id}`)}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[320px_minmax(0,1fr)_340px]">
        <form className="card flex flex-col gap-3.5 p-5" onSubmit={(e) => e.preventDefault()}>
          <h2 className="m-0 text-[15px]">{t('simulate.locationContext')}</h2>
          <div className="flex flex-col gap-0.5 rounded-[10px] bg-ground px-3 py-2.5">
            <span className="eyebrow">{t('simulate.region')}</span>
            <span className="text-sm font-semibold">{simulation?.region_name ?? region?.name ?? state.country}</span>
            <span className="font-mono text-[12px] text-ink-2">
              {simulation?.climate_zone_label ?? '…'} · {simulation?.currency ?? region?.currency} · {simulation?.area_unit ?? region?.units.area}
            </span>
          </div>
          <label className="flex flex-col gap-1 text-[12px] text-ink-2">
            {t('simulate.species')}
            <select className="field-input h-10" value={state.species} onChange={(e) => setState((s) => ({ ...s, species: e.target.value }))}>
              {species.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.common_name} — {s.scientific_name}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1.5 text-[12px] text-ink-2">
            <span className="flex justify-between">
              <span>{t('simulate.treeCount')}</span>
              <span className="font-mono text-sm font-semibold text-ink">{t('simulate.treesLine', { count: state.trees, density: Math.round(state.trees / state.area) })}</span>
            </span>
            <input type="range" min={0} max={2000} step={10} value={state.trees} onChange={(e) => setState((s) => ({ ...s, trees: Number(e.target.value) }))} className="range-input" />
            <span className="flex justify-between font-mono text-[11px] text-muted">
              <span>0</span>
              <span>500</span>
              <span>1000</span>
              <span>1500</span>
              <span>2000</span>
            </span>
          </label>
          <div className="grid grid-cols-2 gap-2.5">
            <label className="flex flex-col gap-1 text-[12px] text-ink-2">
              {t('simulate.plantingYear')}
              <input type="number" className="field-input h-10" min={1950} max={new Date().getFullYear()} value={state.year} onChange={(e) => setState((s) => ({ ...s, year: Number(e.target.value) || s.year }))} />
            </label>
            <label className="flex flex-col gap-1 text-[12px] text-ink-2">
              {t('simulate.plotArea')}
              <input type="number" className="field-input h-10" min={0.01} step={0.01} value={state.area} readOnly={Boolean(plot)} onChange={(e) => setState((s) => ({ ...s, area: Number(e.target.value) || s.area }))} />
            </label>
          </div>
          <fieldset className="m-0 border-0 p-0">
            <legend className="mb-1.5 text-[12px] text-ink-2">{t('simulate.horizon')}</legend>
            <div className="flex gap-1.5">
              {([10, 20, 30] as const).map((h) => (
                <button
                  key={h}
                  type="button"
                  aria-pressed={state.horizon === h}
                  onClick={() => setState((s) => ({ ...s, horizon: h }))}
                  className={`h-9 flex-1 rounded-[8px] border text-[13px] font-semibold ${state.horizon === h ? 'border-forest bg-mint text-forest-deep' : 'border-line bg-surface text-ink-2'}`}
                >
                  {t('simulate.years', { count: h })}
                </button>
              ))}
            </div>
          </fieldset>
          <p className="m-0 text-[12px] leading-relaxed text-muted">{t('simulate.note')}</p>
        </form>

        <figure className="relative m-0 flex min-h-[460px] flex-col overflow-hidden rounded-[14px] border border-line bg-surface">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line px-3.5 py-2.5">
            <span className="text-[13px] font-semibold text-ink">
              {t('simulate.sceneChip', { plot: plot?.name ?? t('simulate.scenarioPlot'), area: `${formatNumber(state.area, locale, { maximumFractionDigits: 2 })} ha`, count: state.trees, species: speciesEntry?.common_name.toLowerCase() ?? state.species, year: standYear })}
            </span>
            <div className="ml-auto flex items-center gap-2">
            {webgl && (
              <div role="group" aria-label={t('land3d.view3d')} className="flex gap-0.5 rounded-[8px] bg-ground p-0.5">
                {(['3d', '2d'] as const).map((v) => (
                  <button
                    key={v}
                    type="button"
                    aria-pressed={view === v}
                    onClick={() => setView(v)}
                    className={`h-7 rounded-[6px] px-2.5 text-[12px] font-semibold ${view === v ? 'bg-surface text-forest-deep shadow-sm' : 'text-ink-2'}`}
                  >
                    {v === '3d' ? t('land3d.view3d') : t('land3d.view2d')}
                  </button>
                ))}
              </div>
            )}
            <button
              type="button"
              aria-label={playing ? t('simulate.scenePause') : t('simulate.scenePlay')}
              aria-pressed={playing}
              onClick={() => setPlaying((p) => !p)}
              className="flex h-8 w-8 items-center justify-center rounded-[7px] bg-mint text-forest-deep"
            >
              {playing ? <Pause size={15} aria-hidden="true" /> : <Play size={15} aria-hidden="true" />}
            </button>
            </div>
          </div>
          <div className="min-h-[320px] flex-1 bg-[#F4F8EF]">
            {view === '3d' && webgl ? (
              <Suspense fallback={<div className="flex h-[540px] items-center justify-center text-[13px] text-muted">{t('land3d.loading')}</div>}>
                <LandView3D
                  ring={ring}
                  boundarySaved={Boolean(plot?.geometry)}
                  treeCount={state.trees}
                  areaHectares={state.area}
                  growth={growth}
                  age={age}
                  standYear={standYear}
                  species={speciesEntry}
                  speciesName={speciesEntry?.common_name ?? state.species}
                  carbon={yearCarbon}
                  locale={locale}
                />
              </Suspense>
            ) : (
              <StandIllustration treeCount={state.trees} growth={growth} canopyTone={canopyTone} label={t('simulate.illustrationLabel', { year: standYear, age })} />
            )}
          </div>
          <div className="flex items-center gap-3 border-t border-line bg-surface px-4 py-3">
            <label className="flex flex-1 flex-col gap-1 text-[12px] text-ink-2">
              <span className="flex flex-wrap justify-between gap-1">
                <span>{t('simulate.standYear')}</span>
                <span className="font-mono text-ink">{t('simulate.standLine', { year: standYear, age, canopy: Math.round(growth * 100) })}</span>
              </span>
              <input type="range" min={state.year} max={horizonEnd} step={1} value={standYear} onChange={(e) => setStandYear(Number(e.target.value))} className="range-input" />
            </label>
            {view === '2d' && state.trees > MAX_GLYPHS && (
              <span className="hidden max-w-[180px] text-right text-[11px] text-muted md:block">{t('simulate.glyphNote', { per: Math.round(state.trees / MAX_GLYPHS) })}</span>
            )}
          </div>
        </figure>

        <section className="flex flex-col gap-3">
          <article className="card-dark flex flex-col gap-1.5 p-4">
            <span className="eyebrow text-mint-on-dark">{t('simulate.annualAverage', { years: state.horizon })}</span>
            <span className="big-number text-[32px] leading-none text-white">
              {simulation ? formatRange(simulation.annual, locale, 1) : <span className="skeleton inline-block h-8 w-32" />}
              {simulation && <span className="ml-2 text-[14px] font-medium text-mint-on-dark">{unitLabel(simulation.annual.unit)}</span>}
            </span>
            <span className="font-mono text-[12px] text-mint-on-dark">
              {simulation ? `${t('results.central').toLowerCase()} ${formatNumber(simulation.annual.central, locale)} · ${t('cards.confidence').toLowerCase()} ${t(`confidence.${simulation.confidence}`)} · certified: no` : '…'}
            </span>
          </article>
          <article className="card flex flex-col gap-1.5 p-4">
            <span className="eyebrow text-forest-deep">{t('simulate.cumulative', { years: state.horizon })}</span>
            <span className="big-number text-[28px] leading-none">
              {simulation ? formatNumber(simulation.series[simulation.series.length - 1]?.cum_central ?? 0, locale, { maximumFractionDigits: 0 }) : '—'}{' '}
              <span className="text-[14px] font-medium text-muted">tCO₂e</span>
            </span>
            <span className="font-mono text-[12px] text-ink-2">
              {simulation
                ? `${t('cards.range').toLowerCase()} ${formatNumber(simulation.series[simulation.series.length - 1]?.cum_low ?? 0, locale, { maximumFractionDigits: 0 })} – ${formatNumber(simulation.series[simulation.series.length - 1]?.cum_high ?? 0, locale, { maximumFractionDigits: 0 })}`
                : ''}
            </span>
          </article>
          <article className="card flex flex-col gap-2 p-4">
            <span className="eyebrow text-forest-deep">{t('simulate.valuePerYear')}</span>
            <table className="w-full border-collapse text-[13px]">
              <tbody>
                {(simulation?.value_scenarios ?? []).map((v) => (
                  <tr key={v.id} className={`border-b border-line last:border-0 ${v.id === 'reference' ? 'font-semibold' : ''}`}>
                    <td className="py-1.5 text-ink-2">{t(`results.${v.id === 'reference' ? 'central' : v.id}`, { defaultValue: v.id })}</td>
                    <td className="py-1.5 text-right font-mono">{formatCurrency(v.price_per_tco2e, v.currency_symbol, locale)}/t</td>
                    <td className="py-1.5 text-right font-mono">{formatCurrency(v.value_per_year.central, v.currency_symbol, locale)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="m-0 text-[11px] leading-relaxed text-amber-text">{simulation?.market_disclaimer ?? t('results.marketNote')}</p>
          </article>
          {activeProgramme && (
            <a href={activeProgramme.url ?? '#'} target="_blank" rel="noopener noreferrer" className="flex items-center justify-between gap-2 rounded-[12px] border border-forest bg-mint px-4 py-3.5 text-[13px] font-semibold text-forest-deep no-underline">
              <span>
                {t('simulate.programmeLink', { country: t(`country.${regionId}`) })}
                <span className="block text-[12px] font-normal">{simulation?.programmes.map((p) => p.name).join(' · ')}</span>
              </span>
              <ExternalLink size={16} aria-hidden="true" />
            </a>
          )}
        </section>
      </div>

      <ExplainPanel body={baseBody} locale={locale} />

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1fr)_420px]">
        <CreditPathway programmes={simulation?.programmes ?? []} regionName={simulation?.region_name ?? region?.name ?? state.country} />
        <CostPanel
          draft={costDraft}
          onChange={setCostDraft}
          scenario={simulation?.cost_scenario}
          currency={simulation?.currency ?? region?.currency ?? ''}
          symbol={simulation?.currency_symbol ?? ''}
          locale={locale}
          horizon={state.horizon}
          plotId={plot?.plot_id ?? null}
          language={language}
        />
      </div>

      <section className="card flex flex-col gap-3 p-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="m-0 text-[15px]">{t('simulate.comparisonTitle')}</h2>
          <span className="text-[12px] text-muted">{t('simulate.comparisonSubtitle')}</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] border-collapse text-[13px]">
            <thead>
              <tr className="text-left text-[12px] text-muted">
                {['colRegion', 'colClimate', 'colAnnual', 'colValue', 'colPathway', 'colLink'].map((k) => (
                  <th key={k} className={`border-b border-line px-2.5 py-2 font-medium ${k === 'colAnnual' || k === 'colValue' ? 'text-right' : ''}`}>
                    {t(`simulate.${k}`)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(simulation?.comparison ?? []).map((row) => (
                <tr key={row.country} className={`border-b border-[#EEF2EF] ${row.country === regionId ? 'bg-mint/40' : ''}`}>
                  <td className="px-2.5 py-2.5 font-semibold">{row.name ?? t(`country.${row.country}`)}</td>
                  <td className="px-2.5 py-2.5 text-ink-2">{row.climate_zone_label ?? row.climate_zone}</td>
                  <td className="px-2.5 py-2.5 text-right font-mono">{formatRange(row.annual, locale, 1)}</td>
                  <td className="px-2.5 py-2.5 text-right font-mono">{formatCurrency(row.reference_value_per_year, row.currency_symbol, locale)}</td>
                  <td className="px-2.5 py-2.5 text-ink-2">{row.programme_summary}</td>
                  <td className="px-2.5 py-2.5">
                    {row.url && (
                      <a href={row.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 font-semibold text-forest">
                        {t('simulate.openProgramme')} <ExternalLink size={12} aria-hidden="true" />
                      </a>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="flex flex-wrap items-center gap-2.5 rounded-[10px] bg-ground px-3 py-2.5">
          <span className="text-[12px] text-muted">{t('simulate.shareTitle')} · {t('simulate.shareText')}</span>
          <code className="font-mono text-[12px] text-ink">{shareUrl(state).replace(/^https?:\/\//, '')}</code>
          <Button size="sm" variant="secondary" className="ml-auto" onClick={() => void copyLink()}>
            <Link2 size={14} aria-hidden="true" /> {copied ? t('app.copied') : t('simulate.copyLink')}
          </Button>
        </div>
      </section>
    </div>
  );
}
