import { useTranslation } from 'react-i18next';
import { unitLabel } from '@/lib/format';
import { ageClassSpan, formatRangeParts, isAgeClassId } from '../logic/treeAgeLogic';
import type { AgeClass, AgeClassRange, CarbonRange } from '../types';

interface HeadlineCardsProps {
  stored: CarbonRange;
  annual: CarbonRange;
  ageClass: AgeClass;
  /** Age class limits from the rules endpoint, for the "21–49 years" caption. */
  ageClasses?: AgeClassRange[];
  locale: string;
  /** The numbers on screen belong to the previous inputs and are being replaced. */
  updating?: boolean;
}

function CarbonCard({
  title,
  help,
  range,
  locale,
}: {
  title: string;
  help: string;
  range: CarbonRange;
  locale: string;
}) {
  const { t } = useTranslation();
  const parts = formatRangeParts(range, locale);
  return (
    <article aria-label={title} className="card flex flex-col gap-1.5 p-4 md:p-5">
      <h3 className="eyebrow m-0 font-mono text-[11px] font-normal">{title}</h3>
      <p className="m-0 flex flex-wrap items-baseline gap-x-2">
        <span className="big-number text-[34px] leading-none text-ink">{parts.central}</span>
        <span className="text-[14px] font-medium text-ink-2">{unitLabel(range.unit)}</span>
      </p>
      <p className="m-0 font-mono text-[12.5px] text-ink-2">
        <span className="sr-only">{t('treeAge.range')}: </span>
        {parts.low} – {parts.high}
      </p>
      <p className="m-0 text-[12.5px] leading-snug text-muted">{help}</p>
    </article>
  );
}

/** Exactly three numbers: carbon stored now, carbon removed each year now, and the age class. */
export function HeadlineCards({
  stored,
  annual,
  ageClass,
  ageClasses,
  locale,
  updating = false,
}: HeadlineCardsProps) {
  const { t } = useTranslation();
  const known = isAgeClassId(ageClass.id);
  const className = known
    ? t(`treeAge.ageClass.${ageClass.id}`)
    : ageClass.label || t('treeAge.ageClass.unknown');
  const span = ageClassSpan(ageClass.id, ageClasses);
  const caption = span
    ? span.max === null
      ? t('treeAge.ageSpanOpen', { min: span.min })
      : t('treeAge.ageSpan', { min: span.min, max: span.max })
    : '';

  return (
    <section
      aria-label={t('treeAge.headlineLabel')}
      aria-busy={updating}
      className={`grid grid-cols-1 gap-3 transition-opacity md:grid-cols-3 ${updating ? 'opacity-60' : ''}`}
    >
      <CarbonCard
        title={t('treeAge.headline.stored.title')}
        help={t('treeAge.headline.stored.help')}
        range={stored}
        locale={locale}
      />
      <CarbonCard
        title={t('treeAge.headline.annual.title')}
        help={t('treeAge.headline.annual.help')}
        range={annual}
        locale={locale}
      />
      <article
        aria-label={t('treeAge.headline.ageClass.title')}
        className="card flex flex-col gap-1.5 p-4 md:p-5"
      >
        <h3 className="eyebrow m-0 font-mono text-[11px] font-normal">
          {t('treeAge.headline.ageClass.title')}
        </h3>
        <p className="m-0">
          <span className="big-number text-[34px] leading-none text-ink">{className}</span>
        </p>
        <p className="m-0 font-mono text-[12.5px] text-ink-2">{caption || ' '}</p>
        <p className="m-0 text-[12.5px] leading-snug text-muted">
          {t('treeAge.headline.ageClass.help')}
        </p>
      </article>
    </section>
  );
}
