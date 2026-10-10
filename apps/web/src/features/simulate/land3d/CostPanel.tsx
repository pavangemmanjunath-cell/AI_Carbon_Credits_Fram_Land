import { useMutation } from '@tanstack/react-query';
import { Bot } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Button } from '@/components/ui/Button';
import { formatCurrency, formatNumber } from '@/lib/format';
import { agentsApi } from '@/services/agentsApi';
import type { CostScenario } from '@/types/api';
import { toCostInputs, COST_FIELDS, type CostDraft, type CostField } from './costs';
import './i18n';

const LABEL: Record<CostField, string> = {
  sapling_per_tree: 'land3d.sapling',
  planting_per_tree: 'land3d.planting',
  maintenance_per_ha_per_year: 'land3d.maintenance',
  monitoring_per_year: 'land3d.monitoring',
};

interface Props {
  draft: CostDraft;
  onChange: (draft: CostDraft) => void;
  scenario: CostScenario | null | undefined;
  currency: string;
  symbol: string;
  locale: string;
  horizon: number;
  /** A saved plot with an inventory lets the agents answer; otherwise the button explains why not. */
  plotId: string | null;
  language: string;
}

export function CostPanel({
  draft,
  onChange,
  scenario,
  currency,
  symbol,
  locale,
  horizon,
  plotId,
  language,
}: Props) {
  const { t } = useTranslation();
  const costs = toCostInputs(draft);
  const ask = useMutation({
    mutationFn: () =>
      agentsApi.ask({
        question: t('land3d.askQuestion'),
        plot_id: plotId as string,
        locale: language,
        costs,
      }),
  });
  const answer = ask.data?.messages
    .filter((m) => m.agent === 'market' && m.kind === 'finding')
    .at(-1);
  const money = (v: number | null | undefined) => formatCurrency(v, symbol, locale);
  const reference = scenario?.price_scenarios.find((s) => s.id === 'reference');

  return (
    <section className="card flex flex-col gap-3 p-5" aria-labelledby="cost-panel-title">
      <div className="flex flex-col gap-1">
        <h2 id="cost-panel-title" className="m-0 text-[15px]">
          {t('land3d.costTitle')}
        </h2>
        <p className="m-0 text-[12px] leading-relaxed text-ink-2">
          {t('land3d.costNote', { currency })}
        </p>
      </div>
      <div className="grid grid-cols-2 gap-2.5">
        {COST_FIELDS.map((field) => (
          <label key={field} className="flex flex-col gap-1 text-[12px] text-ink-2">
            {t(LABEL[field])}
            <input
              type="number"
              inputMode="decimal"
              min={0}
              step="any"
              placeholder="—"
              className="field-input h-10"
              value={draft[field]}
              onChange={(e) => onChange({ ...draft, [field]: e.target.value })}
            />
          </label>
        ))}
      </div>

      {scenario && (
        <div className="flex flex-col gap-1.5 rounded-[12px] bg-ground p-3">
          <div className="flex items-baseline justify-between gap-2">
            <span className="text-[12px] text-ink-2">
              {t('land3d.totalCost', { years: horizon })}
            </span>
            <span className="font-mono text-[15px] font-semibold">
              {money(scenario.total_cost)}
            </span>
          </div>
          <div className="flex items-baseline justify-between gap-2">
            <span className="text-[12px] text-ink-2">{t('land3d.breakEven')}</span>
            <span className="text-right font-mono text-[15px] font-semibold text-forest-deep">
              {money(scenario.break_even_price_per_tco2e.central)}{' '}
              <span className="text-[11px] font-normal text-muted">{t('land3d.perTonne')}</span>
              <span className="block text-[11px] font-normal text-muted">
                {money(scenario.break_even_price_per_tco2e.low)} –{' '}
                {money(scenario.break_even_price_per_tco2e.high)}
              </span>
            </span>
          </div>
          {reference && reference.share_of_costs_covered_pct !== null && (
            <span className="text-[12px] text-ink-2">
              {t('land3d.scenarioCovers', {
                scenario: t('land3d.scenario.reference'),
                price: money(reference.price_per_tco2e),
                pct: formatNumber(reference.share_of_costs_covered_pct, locale, {
                  maximumFractionDigits: 0,
                }),
              })}
            </span>
          )}
          {scenario.not_entered.length > 0 && (
            <span className="text-[11.5px] text-muted">
              {t('land3d.notEntered', {
                list: scenario.not_entered.map((f) => t(`land3d.costFields.${f}`)).join(', '),
              })}
            </span>
          )}
          <span className="text-[11px] leading-relaxed text-amber-text">
            {t('land3d.costDisclaimer')}
          </span>
        </div>
      )}

      {plotId ? (
        <Button variant="secondary" disabled={!costs || ask.isPending} onClick={() => ask.mutate()}>
          <Bot size={15} aria-hidden="true" />{' '}
          {ask.isPending ? t('land3d.asking') : t('land3d.askAgents')}
        </Button>
      ) : (
        <p className="m-0 text-[12px] text-muted">{t('land3d.askNeedsPlot')}</p>
      )}
      {ask.isError && (
        <p role="alert" className="m-0 text-[12px] text-amber-text">
          {t('land3d.askFailed', {
            error: ask.error instanceof Error ? ask.error.message : String(ask.error),
          })}
        </p>
      )}
      {answer && (
        <blockquote className="m-0 rounded-[10px] border-l-4 border-forest bg-mint/50 px-3 py-2 text-[12.5px] leading-relaxed text-ink">
          <span className="mb-0.5 block text-[11px] font-semibold text-forest-deep">
            {answer.agent_title}
          </span>
          {answer.text}
        </blockquote>
      )}
    </section>
  );
}
