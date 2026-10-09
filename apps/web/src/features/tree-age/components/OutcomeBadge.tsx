import {
  CircleCheck,
  CircleHelp,
  CircleMinus,
  CircleX,
  Coins,
  ShieldCheck,
  type LucideIcon,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { humanize, outcomeStyle, type OutcomeIcon, type OutcomeTone } from '../logic/treeAgeLogic';

const TONES: Record<OutcomeTone, string> = {
  rose: 'border-rose-300 bg-rose-100 text-rose-900',
  green: 'border-forest/40 bg-mint text-forest-deep',
  amber: 'border-amber-text/40 bg-amber-tint text-amber-text',
  blue: 'border-blue-text/30 bg-blue-tint text-blue-text',
  violet: 'border-violet-300 bg-violet-100 text-violet-900',
  grey: 'border-line bg-ground text-ink-2',
};

const ICONS: Record<OutcomeIcon, LucideIcon> = {
  x: CircleX,
  check: CircleCheck,
  help: CircleHelp,
  shield: ShieldCheck,
  coins: Coins,
  minus: CircleMinus,
};

/**
 * What a rule means for these trees. Colour, icon and word always travel together, so the
 * meaning never depends on colour alone.
 */
export function OutcomeBadge({ outcome }: { outcome: string }) {
  const { t } = useTranslation();
  const style = outcomeStyle(outcome);
  const Icon = ICONS[style.icon];
  return (
    <span
      data-outcome={outcome}
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[12px] font-semibold leading-none ${TONES[style.tone]}`}
    >
      <Icon size={13} aria-hidden="true" />
      {t(`treeAge.outcome.${style.labelKey}`, { defaultValue: humanize(outcome) })}
    </span>
  );
}
