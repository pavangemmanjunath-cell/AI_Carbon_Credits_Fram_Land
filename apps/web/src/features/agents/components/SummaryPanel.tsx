import { Flag, TriangleAlert } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { formatClock, formatQuantity } from '../logic/agentsLogic';
import { unitLabel } from '@/lib/format';
import type { AgentNames } from '../useAgentNames';
import type { AgentMessage, AgentRunSummary } from '../types';
import { AgentAvatar } from './AgentAvatar';

interface SummaryPanelProps {
  /** The coordinator's `summary` message, when the transcript has one. */
  message: AgentMessage | null;
  summary: AgentRunSummary | null;
  names: AgentNames;
  locale: string;
}

/** The final result: headline, estimate range, readiness and next steps, in the forest-green panel. */
export function SummaryPanel({ message, summary, names, locale }: SummaryPanelProps) {
  const { t } = useTranslation();
  const agent = message?.agent ?? 'coordinator';
  const headline = summary?.headline || message?.text || '';
  const extraText = message?.text && message.text !== headline ? message.text : '';
  const estimate = summary?.estimate ?? null;
  const readiness = summary?.readiness ?? null;
  const nextSteps = summary?.next_steps ?? [];
  const clock = formatClock(message?.created_at, locale);

  return (
    <article
      aria-label={t('agentsPage.summaryTitle')}
      className="rounded-[14px] bg-forest p-5 text-white shadow-float transition duration-300 starting:translate-y-1 starting:opacity-0 md:p-6"
    >
      <header className="flex flex-wrap items-center gap-x-2.5 gap-y-1">
        <AgentAvatar agent={agent} size="md" />
        <span className="text-[14px] font-semibold">{names.title(agent)}</span>
        <span className="inline-flex items-center gap-1.5 rounded-full bg-white/15 px-2.5 py-1 text-[11px] font-semibold leading-none">
          <Flag size={12} aria-hidden="true" />
          {t('agentsPage.kind.summary')}
        </span>
        {clock && (
          <time
            dateTime={message?.created_at}
            className="ml-auto font-mono text-[11px] text-mint-on-dark"
          >
            {clock}
          </time>
        )}
      </header>

      <p className="mb-0 mt-4 font-heading text-[20px] font-semibold leading-snug">{headline}</p>
      {extraText && (
        <p className="mb-0 mt-2 text-[15px] leading-relaxed text-white/90">{extraText}</p>
      )}

      {(estimate || readiness !== null) && (
        <div className="mt-5 flex flex-wrap items-end gap-x-10 gap-y-4">
          {estimate && (
            <div className="flex flex-col gap-1">
              <span className="eyebrow text-mint-on-dark">{t('agentsPage.summaryEstimate')}</span>
              <span className="big-number text-[38px] leading-none">
                {formatQuantity(estimate.central, locale)}{' '}
                <span className="text-[15px] font-medium text-mint-on-dark">
                  {unitLabel(estimate.unit)}
                </span>
              </span>
              <span className="font-mono text-[12.5px] text-mint-on-dark">
                {t('agentsPage.summaryRange', {
                  low: formatQuantity(estimate.low, locale),
                  high: formatQuantity(estimate.high, locale),
                })}
              </span>
            </div>
          )}
          {readiness !== null && (
            <div className="flex min-w-[160px] flex-col gap-1.5">
              <span className="eyebrow text-mint-on-dark">{t('agentsPage.summaryReadiness')}</span>
              <span className="big-number text-[28px] leading-none">
                {Math.round(readiness)}
                <span className="text-[15px] font-medium text-mint-on-dark">/100</span>
              </span>
              <span
                className="block h-2 overflow-hidden rounded-full bg-white/20"
                aria-hidden="true"
              >
                <span
                  className="block h-full rounded-full bg-white"
                  style={{ width: `${Math.min(100, Math.max(0, readiness))}%` }}
                />
              </span>
            </div>
          )}
        </div>
      )}

      {nextSteps.length > 0 && (
        <div className="mt-5 flex flex-col gap-1.5">
          <span className="eyebrow text-mint-on-dark">{t('agentsPage.summaryNextSteps')}</span>
          <ol className="m-0 flex list-decimal flex-col gap-1 pl-5 text-[14.5px] leading-snug">
            {nextSteps.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
        </div>
      )}

      <p className="mb-0 mt-5 flex flex-wrap items-center gap-x-2 gap-y-1 border-t border-white/20 pt-3 text-[13px] text-mint-on-dark">
        <TriangleAlert size={15} aria-hidden="true" className="shrink-0" />
        <span>{t('agentsPage.notCredit')}</span>
        <span className="font-mono text-[12px]">{t('agentsPage.certifiedNo')}</span>
      </p>
    </article>
  );
}
