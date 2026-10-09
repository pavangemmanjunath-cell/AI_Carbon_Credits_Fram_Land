import { Sprout } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { AGE_MAX, AGE_MIN, AGE_SLIDER_MAX, checkWholeNumber } from '../logic/treeAgeLogic';
import { useNumberDraft, type DraftParse } from '../useNumberDraft';

interface AgeFieldProps {
  age: number;
  onChange: (age: number) => void;
}

/** A slider and a number box for the same thing, so it can be dragged or typed. 0 = planning. */
export function AgeField({ age, onChange }: AgeFieldProps) {
  const { t } = useTranslation();
  const parse = (text: string): DraftParse => {
    const checked = checkWholeNumber(text, AGE_MIN, AGE_MAX);
    return checked.ok
      ? checked
      : {
          ok: false,
          message: t(`treeAge.problem.${checked.problem}`, { min: AGE_MIN, max: AGE_MAX }),
        };
  };
  const {
    text,
    error,
    onChange: onType,
    onBlur,
  } = useNumberDraft({
    value: age,
    parse,
    onCommit: (value) => {
      if (value !== null) onChange(value);
    },
  });
  const planning = age === 0;

  return (
    <div className="flex flex-col">
      <label htmlFor="tree-age-age" className="mb-1.5 text-[12px] font-medium text-ink-2">
        {t('treeAge.age')}
      </label>
      <div className="flex items-center gap-3">
        <input
          type="range"
          className="range-input min-w-0 flex-1"
          min={AGE_MIN}
          max={AGE_SLIDER_MAX}
          step={1}
          value={Math.min(age, AGE_SLIDER_MAX)}
          onChange={(event) => onChange(Number(event.target.value))}
          aria-label={t('treeAge.ageSlider')}
          aria-valuetext={
            planning ? t('treeAge.ageZeroText') : t('treeAge.ageYears', { count: age })
          }
        />
        <span
          className={`flex w-[92px] shrink-0 overflow-hidden rounded-[10px] border bg-surface focus-within:shadow-[0_0_0_3px_var(--mint)] ${
            error ? 'border-rose-600' : 'border-line focus-within:border-forest'
          }`}
        >
          <input
            id="tree-age-age"
            type="text"
            inputMode="numeric"
            autoComplete="off"
            value={text}
            onChange={onType}
            onBlur={onBlur}
            aria-invalid={error ? true : undefined}
            aria-describedby="tree-age-age-hint tree-age-age-error"
            className="h-10 min-w-0 flex-1 bg-transparent px-2.5 text-right font-mono text-[15px] outline-none"
          />
        </span>
      </div>
      <p
        id="tree-age-age-hint"
        className={`m-0 mt-1.5 flex items-center gap-1.5 text-[12px] leading-snug ${
          planning ? 'font-semibold text-forest-deep' : 'text-muted'
        }`}
      >
        {planning && <Sprout size={14} aria-hidden="true" className="shrink-0" />}
        {planning ? t('treeAge.agePlanning') : t('treeAge.ageHint')}
      </p>
      <p
        id="tree-age-age-error"
        aria-live="polite"
        className="m-0 mt-1 text-[12px] font-medium text-rose-700 empty:mt-0"
      >
        {error}
      </p>
    </div>
  );
}
