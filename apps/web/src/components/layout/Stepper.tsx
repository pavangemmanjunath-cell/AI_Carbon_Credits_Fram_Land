import { Check } from 'lucide-react';
import { useTranslation } from 'react-i18next';

export type StepKey = 'selectLand' | 'addTrees' | 'analyze' | 'carbonPotential';
const ORDER: StepKey[] = ['selectLand', 'addTrees', 'analyze', 'carbonPotential'];

interface StepperProps {
  current: StepKey;
  completed?: StepKey[];
}

/** Four-step progress strip (kept deliberately simple on the main screen). */
export function Stepper({ current, completed = [] }: StepperProps) {
  const { t } = useTranslation();
  const currentIndex = ORDER.indexOf(current);
  return (
    <ol aria-label={t('steps.progress')} className="flex min-w-0 flex-1 flex-wrap items-center gap-1 lg:gap-1.5">
      {ORDER.map((key, index) => {
        const done = completed.includes(key) || index < currentIndex;
        const active = key === current;
        return (
          <li key={key} className="flex items-center gap-1 lg:gap-1.5">
            <span
              aria-current={active ? 'step' : undefined}
              className={`flex items-center gap-2.5 rounded-[10px] px-2 py-1.5 lg:px-2.5 ${active ? 'bg-mint' : ''}`}
            >
              <span
                className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-[12px] font-bold ${
                  done
                    ? 'bg-forest text-white'
                    : active
                      ? 'bg-panel-dark text-white'
                      : 'border-[1.5px] border-line text-ink-2'
                }`}
              >
                {done ? <Check size={14} aria-hidden="true" /> : index + 1}
              </span>
              <span className="hidden flex-col leading-tight xl:flex">
                <span className={`text-[13px] font-semibold ${active ? 'text-forest-deep' : 'text-ink-2'}`}>
                  {t(`steps.${key}`)}
                </span>
                <span className="text-[11px] text-muted">{t(`steps.${key}Hint`)}</span>
              </span>
              <span className={`text-[13px] font-semibold xl:hidden ${active ? 'text-forest-deep' : 'text-ink-2'}`}>
                {t(`steps.${key}`)}
              </span>
            </span>
            {index < ORDER.length - 1 && (
              <span aria-hidden="true" className="px-0.5 text-line">
                ›
              </span>
            )}
          </li>
        );
      })}
    </ol>
  );
}
