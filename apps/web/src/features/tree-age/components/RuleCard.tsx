import { ExternalLink, ShieldCheck, TriangleAlert } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import {
  amountUnitKey,
  formatAmountValue,
  humanize,
  outcomeOf,
  safeHttpUrl,
  verificationOf,
} from '../logic/treeAgeLogic';
import type { TreeAgeRule } from '../types';
import { OutcomeBadge } from './OutcomeBadge';

interface RuleCardProps {
  rule: TreeAgeRule;
  locale: string;
  /** A rule that does not apply is shown smaller, with the reason instead of an outcome. */
  muted?: boolean;
}

function Chip({ children, tone = 'grey' }: { children: string; tone?: 'grey' | 'amber' }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-1 text-[11.5px] font-medium leading-none ${
        tone === 'amber'
          ? 'border-amber-text/40 bg-amber-tint text-amber-text'
          : 'border-line bg-ground text-ink-2'
      }`}
    >
      {children}
    </span>
  );
}

/** One law or programme: what it is, what it means for these trees, and where it comes from. */
export function RuleCard({ rule, locale, muted = false }: RuleCardProps) {
  const { t } = useTranslation();
  const verified = verificationOf(rule) === 'verified';
  const sources = rule.sources
    .map((source) => ({ ...source, href: safeHttpUrl(source.url) }))
    .filter((source) => source.title || source.href);
  const unitKey = rule.amount ? amountUnitKey(rule.amount.unit) : null;

  return (
    <article
      aria-label={rule.name}
      data-applies={rule.applies}
      className={`card flex flex-col gap-2 ${muted ? 'p-3.5' : 'p-4'}`}
    >
      <div className="flex flex-wrap items-center gap-2">
        {!muted && <OutcomeBadge outcome={outcomeOf(rule)} />}
        {rule.category && (
          <Chip>
            {t(`treeAge.category.${rule.category}`, { defaultValue: humanize(rule.category) })}
          </Chip>
        )}
        {rule.is_example && <Chip tone="amber">{t('treeAge.example')}</Chip>}
        {rule.status && rule.status !== 'in-force' && (
          <Chip tone="amber">
            {t(`treeAge.status.${rule.status}`, { defaultValue: humanize(rule.status) })}
          </Chip>
        )}
      </div>

      <h3 className="m-0 text-[15px] leading-snug">{rule.name}</h3>
      {rule.authority && <p className="m-0 text-[13px] text-muted">{rule.authority}</p>}
      {muted && rule.why && (
        <p className="m-0 text-[13.5px] font-medium leading-snug text-ink">{rule.why}</p>
      )}
      {rule.summary && (
        <p className={`m-0 leading-relaxed ${muted ? 'text-[13px] text-ink-2' : 'text-[14px]'}`}>
          {rule.summary}
        </p>
      )}

      {rule.amount && (
        <p className="m-0 font-mono text-[14px] font-semibold text-ink">
          {formatAmountValue(rule.amount, locale)}{' '}
          {unitKey ? t(`treeAge.amountUnit.${unitKey}`) : rule.amount.unit}
          {rule.amount.as_of && (
            <span className="font-normal text-muted">
              {' '}
              ({t('treeAge.asOf', { date: rule.amount.as_of })})
            </span>
          )}
        </p>
      )}

      <p
        className={`m-0 inline-flex items-start gap-1.5 text-[12.5px] font-medium ${
          verified ? 'text-forest-deep' : 'text-amber-text'
        }`}
      >
        {verified ? (
          <ShieldCheck size={15} aria-hidden="true" className="mt-px shrink-0" />
        ) : (
          <TriangleAlert size={15} aria-hidden="true" className="mt-px shrink-0" />
        )}
        {verified ? t('treeAge.verified') : t('treeAge.notVerified')}
      </p>

      {sources.length > 0 && (
        <div className="flex flex-col gap-1">
          <span className="eyebrow">{t('treeAge.sources')}</span>
          <ul className="m-0 flex list-none flex-col gap-1 p-0">
            {sources.map((source, index) => (
              <li key={`${source.title}-${index}`} className="text-[13px] leading-snug">
                {source.href ? (
                  <a
                    href={source.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-baseline gap-1 font-medium text-forest underline-offset-2 hover:underline"
                  >
                    <span>{source.title || source.href}</span>
                    <ExternalLink size={12} aria-hidden="true" className="shrink-0 self-center" />
                    <span className="sr-only">({t('treeAge.opensNewTab')})</span>
                  </a>
                ) : (
                  <span className="text-ink">{source.title}</span>
                )}
                {source.publisher && <span className="text-muted"> · {source.publisher}</span>}
              </li>
            ))}
          </ul>
        </div>
      )}
    </article>
  );
}
