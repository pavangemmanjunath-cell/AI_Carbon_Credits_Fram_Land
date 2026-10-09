import { Info, TriangleAlert } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { outlookKey, type OutlookKey } from '../logic/treeAgeLogic';
import type { CreditOutlook as CreditOutlookData } from '../types';

const TONES: Record<OutlookKey | 'unknown', string> = {
  planned: 'border-forest/30 bg-mint text-forest-deep',
  'not-eligible': 'border-amber-text/30 bg-amber-tint text-amber-text',
  conditional: 'border-blue-text/25 bg-blue-tint text-blue-text',
  eligible: 'border-forest/30 bg-mint text-forest-deep',
  unknown: 'border-line bg-ground text-ink-2',
};

interface CreditOutlookProps {
  outlook: CreditOutlookData;
  /** The trees' age: age 0 means "planning", which has its own sentence. */
  age: number;
}

/**
 * One sentence on whether trees like these usually earn carbon credits, always followed by the
 * reminder that an estimate is not a credit. In English the sentence is the API's own (it names
 * the rules it rests on); other languages get a matching ready-made sentence.
 */
export function CreditOutlook({ outlook, age }: CreditOutlookProps) {
  const { t, i18n } = useTranslation();
  const key = outlookKey(outlook, age);
  const english = (i18n.resolvedLanguage ?? i18n.language ?? 'en').startsWith('en');
  const sentence =
    english && outlook.summary
      ? outlook.summary
      : key
        ? t(`treeAge.outlook.${key}`)
        : outlook.summary;

  return (
    <section
      aria-label={t('treeAge.outlookLabel')}
      className={`flex flex-col gap-2 rounded-[12px] border p-4 ${TONES[key ?? 'unknown']}`}
    >
      {sentence && (
        <p className="m-0 flex items-start gap-2.5 text-[15px] font-medium leading-snug">
          <Info size={18} aria-hidden="true" className="mt-0.5 shrink-0" />
          {sentence}
        </p>
      )}
      <p className="m-0 flex items-start gap-2.5 text-[13px] leading-snug">
        <TriangleAlert size={16} aria-hidden="true" className="mt-px shrink-0" />
        {t('treeAge.notCredit')}
      </p>
    </section>
  );
}
