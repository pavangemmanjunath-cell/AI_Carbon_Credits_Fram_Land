import { useEffect, useState } from 'react';
import { AlertTriangle, Download, FileText, Link2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Link, useParams } from 'react-router';
import { Button, LinkButton } from '@/components/ui/Button';
import { PageSpinner } from '@/components/ui/PageSpinner';
import { copyToClipboard, downloadJson } from '@/lib/download';
import { formatArea, formatCurrency, formatNumber, intlLocale, unitLabel } from '@/lib/format';
import { useAnalysis, useCarbonEstimate, useCube, useExplain, useMarketScenario, usePlot, usePolicyEligibility, useTrees } from '@/services/queries';
import { useUiStore } from '@/store/uiStore';
import { ChangeOverTimeCard } from './ChangeOverTimeCard';
import { CumulativeChart } from './CumulativeChart';
import { PolicyPathways } from './PolicyPathways';
import { ReadinessCard } from './ReadinessCard';
import { evidenceChainLines, explainBody, parameterCounts, resultsExport } from './logic/resultsLogic';
import { latestInventory } from '@/lib/insights';

export default function ResultsPage() {
  const { t } = useTranslation();
  const { id = '' } = useParams();
  const language = useUiStore((s) => s.language);
  const areaUnit = useUiStore((s) => s.areaUnit);
  const setSelectedPlotId = useUiStore((s) => s.setSelectedPlotId);
  const [copied, setCopied] = useState(false);

  const plotQuery = usePlot(id);
  const plot = plotQuery.data;
  const analysis = useAnalysis(id).data;
  const trees = useTrees(id).data;
  const inventory = latestInventory(trees?.items);
  const estimateQuery = useCarbonEstimate(id, inventory?.inventory_id ?? null, Boolean(inventory));
  const estimate = estimateQuery.data;
  const policy = usePolicyEligibility(id).data;
  const cubeQuery = useCube(id, 'ndvi', true);
  const market = useMarketScenario(id, estimate?.estimate_id).data;
  const explain = useExplain(plot && estimate ? explainBody(language, inventory, analysis, estimate, plot) : null).data;
  useEffect(() => {
    if (plot?.plot_id) setSelectedPlotId(plot.plot_id);
  }, [plot?.plot_id, setSelectedPlotId]);

  if (plotQuery.isLoading || !plot) return <PageSpinner />;
  const locale = intlLocale(language, plot.country);
  const area = formatArea(plot.area_hectares, plot.country, locale, areaUnit);

  if (!inventory || !estimate) {
    return (
      <div className="p-6">
        <div className="card flex flex-col items-start gap-3 p-6">
          <h1 className="m-0 text-[22px]">{t('results.title')}</h1>
          <p className="m-0 text-sm text-ink-2">{estimateQuery.isLoading ? t('app.loading') : t('results.noEstimate')}</p>
          <LinkButton to="/app" variant="secondary">
            {t('results.breadcrumbWorkspace')}
          </LinkButton>
        </div>
      </div>
    );
  }

  const counts = parameterCounts(estimate);
  const chain = evidenceChainLines(plot, inventory, analysis, estimate);
  const unit = unitLabel(estimate.estimate.unit);
  const share = async () => {
    const ok = await copyToClipboard(window.location.href);
    setCopied(ok);
    setTimeout(() => setCopied(false), 2000);
  };
  const exportJson = () => downloadJson(resultsExport(plot, inventory, analysis, estimate, { policy, market, explanation: explain }), `${plot.plot_id}-carbon-potential.json`);
  const low = estimate.estimate.low;
  const high = estimate.estimate.high;
  const spanPct = (v: number) => (high > 0 ? Math.min(100, Math.max(0, (v / (high * 1.15)) * 100)) : 0);

  return (
    <div className="mx-auto flex max-w-[1440px] flex-col gap-5 p-5">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex flex-col gap-1.5">
          <nav aria-label="Breadcrumb" className="flex items-center gap-2 text-[13px] text-muted">
            <Link to="/app" className="text-ink-2 no-underline hover:text-forest">{t('results.breadcrumbWorkspace')}</Link>
            <span aria-hidden="true">›</span>
            <span>{plot.name}</span>
            <span aria-hidden="true">›</span>
            <span className="font-semibold text-ink">{t('results.title')}</span>
          </nav>
          <h1 className="m-0 text-[30px] tracking-tight">
            {t('results.title')} — {plot.name}
          </h1>
          <p className="m-0 text-sm text-ink-2">
            {t('results.meta', {
              plot: plot.plot_id,
              area: area.primary,
              trees: inventory.tree_count.toLocaleString(locale),
              species: inventory.species.common_name.toLowerCase(),
              year: inventory.plantation_year,
              region: [plot.region, t(`country.${plot.country}`, { defaultValue: plot.country })].filter(Boolean).join(', '),
            })}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="inline-flex items-center gap-2 rounded-[10px] border border-amber-tint bg-amber-tint px-3.5 py-2.5 text-[13px] font-semibold text-amber-text">
            <AlertTriangle size={16} aria-hidden="true" /> {t('results.pill')}
          </span>
          <Button variant="secondary" size="sm" onClick={exportJson}>
            <Download size={15} aria-hidden="true" /> {t('results.downloadJson')}
          </Button>
          <Button variant="secondary" size="sm" onClick={() => void share()}>
            <Link2 size={15} aria-hidden="true" /> {copied ? t('results.linkCopied') : t('results.sharePrivateLink')}
          </Button>
          <LinkButton to={`/app/plots/${plot.plot_id}/report`} size="sm">
            <FileText size={15} aria-hidden="true" /> {t('results.generateReport')}
          </LinkButton>
        </div>
      </div>

      <section aria-label={t('landing.threeNumbersTitle')} className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <article className="card-dark flex flex-col gap-3 p-5">
          <span className="eyebrow text-mint-on-dark">{t('results.environmentalBenefit')}</span>
          <span className="big-number text-[44px] leading-none text-white">
            {formatNumber(estimate.estimate.central, locale)} <span className="text-[16px] font-medium text-mint-on-dark">{unit}</span>
          </span>
          <div className="flex flex-col gap-1.5">
            <div className="relative h-2.5 rounded-full bg-panel-dark-2">
              <span className="absolute top-0 h-full rounded-full bg-plot-fill" style={{ left: `${spanPct(low)}%`, width: `${Math.max(2, spanPct(high) - spanPct(low))}%` }} />
              <span className="absolute -top-1 h-[18px] w-1 rounded bg-white" style={{ left: `calc(${spanPct(estimate.estimate.central)}% - 2px)` }} />
            </div>
            <div className="flex justify-between font-mono text-[12px] text-mint-on-dark">
              <span>{t('results.low').toLowerCase()} {formatNumber(low, locale)}</span>
              <span>{t('results.central').toLowerCase()} {formatNumber(estimate.estimate.central, locale)}</span>
              <span>{t('results.high').toLowerCase()} {formatNumber(high, locale)}</span>
            </div>
          </div>
          <p className="m-0 text-[13px] leading-relaxed text-[#C9D6CD]">
            {t('results.annualRemoval')} · {t('cards.confidence').toLowerCase()} <strong className="text-white">{t(`confidence.${estimate.confidence}`).toUpperCase()}</strong> · certified: no ·{' '}
            {estimate.stock ? `${t('results.stock').toLowerCase()} ${formatNumber(estimate.stock.central, locale)} ${unitLabel(estimate.stock.unit)}` : ''}
          </p>
        </article>

        <article className="card flex flex-col gap-3 p-5">
          <span className="eyebrow text-forest-deep">{t('results.indicativeValue')}</span>
          {market ? (
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="text-left text-[12px] text-muted">
                  <th className="py-1 font-medium">{t('results.scenario')}</th>
                  <th className="py-1 text-right font-medium">{t('results.price')}</th>
                  <th className="py-1 text-right font-medium">{t('results.valuePerYear')}</th>
                </tr>
              </thead>
              <tbody>
                {market.scenarios.map((s) => (
                  <tr key={s.id} className={`border-t border-line ${s.id === 'reference' ? 'font-semibold' : ''}`}>
                    <td className="py-2">{t(`results.${s.id === 'reference' ? 'central' : s.id}`, { defaultValue: s.id })}</td>
                    <td className="py-2 text-right font-mono">{formatCurrency(s.price_per_tco2e, market.currency_symbol, locale)}</td>
                    <td className="py-2 text-right font-mono">{formatCurrency(s.value_per_year.central, market.currency_symbol, locale)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <span className="skeleton h-24 w-full" />
          )}
          <p className="m-0 text-[12px] leading-relaxed text-amber-text">{t('results.marketNote')}</p>
          {market && <p className="m-0 text-[11px] text-muted">{t('results.basis', { source: market.basis.source, asOf: market.basis.as_of })}</p>}
        </article>

        <article className="card flex flex-col gap-3 p-5">
          <span className="eyebrow text-forest-deep">{t('results.otherIncome')}</span>
          <ul className="m-0 flex list-none flex-col gap-2 p-0 text-sm">
            {(market?.other_income ?? []).map((item) => (
              <li key={item.id} className="flex items-start justify-between gap-2 border-b border-line pb-2 last:border-0">
                <span>
                  {item.label}
                  <span className="block text-[12px] text-muted">{item.source}</span>
                </span>
                <span className="font-mono text-[12px] text-ink-2">{item.value == null ? t('results.enterValue') : formatNumber(item.value, locale)}</span>
              </li>
            ))}
          </ul>
          <p className="m-0 text-[12px] text-ink-2">{t('results.neverSummed')}</p>
        </article>
      </section>

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <CumulativeChart series={estimate.annual_series} locale={locale} />
        </div>
        <section className="card flex flex-col gap-3 p-5">
          <h2 className="m-0 text-[15px]">{t('results.treeDataQuality')}</h2>
          <table className="w-full border-collapse text-sm">
            <tbody>
              {inventory.data_quality.fields.map((f) => (
                <tr key={f.name} className="border-b border-line last:border-0">
                  <td className="py-1.5 capitalize">{f.name.replace('_', ' ')}</td>
                  <td className={`py-1.5 text-right font-semibold ${f.status === 'supplied' ? 'text-forest' : 'text-amber-text'}`}>
                    {f.status === 'supplied' ? '✓' : '✗'} {t(`results.${f.status}`)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="flex items-center justify-between rounded-[10px] bg-ground px-3 py-2.5 text-[13px]">
            <span>{t('cards.confidence')}</span>
            <span className="font-mono font-semibold text-amber-text">{t(`confidence.${estimate.confidence}`).toUpperCase()}</span>
          </div>
          <p className="m-0 text-[12px] text-muted">{t('results.parameterStatus', { ...counts })}</p>
        </section>
      </section>

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <ReadinessCard readiness={estimate.readiness} />
        <div className="lg:col-span-2">{policy ? <PolicyPathways policy={policy} /> : <div className="card h-full min-h-[200px] p-5"><span className="skeleton block h-full w-full" /></div>}</div>
      </section>

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <ChangeOverTimeCard cube={cubeQuery.data} loading={cubeQuery.isLoading} locale={locale} />
        <section className="card flex flex-col gap-3 p-5">
          <h2 className="m-0 text-[15px]">{t('results.plainWords')}</h2>
          <p className="m-0 text-sm leading-relaxed text-ink-2">{explain?.text ?? <span className="skeleton inline-block h-16 w-full" />}</p>
          <div className="flex flex-wrap gap-2">
            <LinkButton to={`/app/simulate?country=${plot.country}&species=${inventory.species.id}&trees=${inventory.tree_count}&year=${inventory.plantation_year}&plot=${plot.plot_id}`} size="sm">
              {t('results.simulateMore')}
            </LinkButton>
            <LinkButton to={`/app/plots/${plot.plot_id}/report`} variant="secondary" size="sm">
              {t('results.previewReport')}
            </LinkButton>
          </div>
          <p className="m-0 text-[12px] text-muted">{t('results.plainWordsNote', { provider: explain?.provider ?? 'template' })}</p>
        </section>
      </section>

      <section className="card flex flex-col gap-3 p-5">
        <h2 className="m-0 text-[15px]">{t('results.evidenceChain')}</h2>
        <pre className="m-0 overflow-x-auto rounded-[10px] bg-panel-dark p-3.5 font-mono text-[12.5px] leading-relaxed text-[#E6EFE9]">{chain.join('\n')}</pre>
      </section>
    </div>
  );
}
