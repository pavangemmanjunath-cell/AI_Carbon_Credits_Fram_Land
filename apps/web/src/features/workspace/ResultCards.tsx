import { CloudSun, Sprout, Vegan } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { formatArea, formatRange, formatSignedPercent, unitLabel } from '@/lib/format';
import { useUiStore } from '@/store/uiStore';
import type { Analysis, CarbonEstimate, Plot, TreeInventory } from '@/types/api';
import { summarize } from './logic/workspaceModel';

interface Props {
  plot: Plot | null;
  inventory: TreeInventory | null;
  estimate?: CarbonEstimate;
  analysis?: Analysis;
  locale: string;
  loading?: boolean;
}

/** Exactly three cards — kept deliberately small so the main screen stays readable. */
export function ResultCards({ plot, inventory, estimate, analysis, locale, loading }: Props) {
  const { t } = useTranslation();
  const areaUnit = useUiStore((s) => s.areaUnit);
  const summary = summarize(estimate, analysis);
  const area = plot ? formatArea(plot.area_hectares, plot.country, locale, areaUnit) : null;
  const skeleton = <span className="skeleton inline-block h-7 w-24 align-middle" aria-hidden="true" />;

  return (
    <section aria-label={t('panel.resultsTitle')} className="grid grid-cols-1 gap-3.5 md:grid-cols-3">
      <article className="card flex items-center gap-3.5 p-4">
        <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-[12px] bg-mint text-forest-deep">
          <Vegan size={22} aria-hidden="true" />
        </span>
        <span className="flex min-w-0 flex-col gap-0.5">
          <span className="text-[12px] text-muted">{t('cards.plotArea')}</span>
          <span className="big-number text-[26px]">{area ? area.primary : '—'}</span>
          <span className="text-[12px] text-ink-2">
            {area ? area.secondary : ''}
            {inventory ? ` · ${inventory.tree_count.toLocaleString(locale)} ${inventory.species.common_name.toLowerCase()}` : ''}
          </span>
        </span>
      </article>
      <article className="card flex items-center gap-3.5 p-4">
        <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-[12px] bg-mint text-forest-deep">
          <Sprout size={22} aria-hidden="true" />
        </span>
        <span className="flex min-w-0 flex-col gap-0.5">
          <span className="text-[12px] text-muted">{t('cards.vegetationHealth')}</span>
          <span className="big-number text-[26px]">
            {summary.ndvi != null ? summary.ndvi.toFixed(2) : loading ? skeleton : '—'}
            {summary.ndviClass && <span className="ml-2 text-[14px] font-medium text-muted">NDVI · {t(`ndvi.${summary.ndviClass}`)}</span>}
          </span>
          <span className="text-[12px] text-ink-2">
            {summary.trendPct != null && analysis?.vegetation?.trend.start
              ? t('cards.trend', { pct: formatSignedPercent(summary.trendPct, locale, 0), start: analysis.vegetation.trend.start.slice(0, 4) })
              : summary.ndviDate
                ? t('cards.latestScene', { date: summary.ndviDate })
                : ''}
          </span>
        </span>
      </article>
      <article className="card-dark flex items-center gap-3.5 p-4">
        <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-[12px] bg-panel-dark-2 text-mint-on-dark">
          <CloudSun size={22} aria-hidden="true" />
        </span>
        <span className="flex min-w-0 flex-col gap-0.5">
          <span className="text-[12px] text-mint-on-dark">{t('cards.estimatedRemoval')}</span>
          <span className="big-number text-[26px] text-white">
            {summary.removal ? formatRange(summary.removal, locale, 1) : loading ? skeleton : '—'}
            {summary.removal && <span className="ml-2 text-[14px] font-medium text-mint-on-dark">{unitLabel(summary.removal.unit)}</span>}
          </span>
          <span className="text-[12px] text-mint-on-dark">{t('cards.notCredit')}</span>
        </span>
      </article>
    </section>
  );
}
