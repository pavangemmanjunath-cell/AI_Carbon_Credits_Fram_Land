import { useState } from 'react';
import { Building2, Check, Link2, Tractor, Trees, type LucideIcon } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Button } from '@/components/ui/Button';
import {
  GIRTH_MAX,
  GIRTH_MIN,
  SETTING_CHOICES,
  TREES_MAX,
  TREES_MIN,
  checkGirth,
  checkWholeNumber,
  countryOptions,
} from '../logic/treeAgeLogic';
import type { Subdivision, TreeAgeInputs, TreeSetting } from '../types';
import type { DraftParse } from '../useNumberDraft';
import { AgeField } from './AgeField';
import { NumberField } from './NumberField';

const SETTING_ICONS: Record<(typeof SETTING_CHOICES)[number], LucideIcon> = {
  farm: Tractor,
  urban: Building2,
  forest: Trees,
};

export interface SpeciesOption {
  id: string;
  common_name: string;
  scientific_name: string;
}

interface InputsCardProps {
  inputs: TreeAgeInputs;
  onChange: (patch: Partial<TreeAgeInputs>) => void;
  species: SpeciesOption[] | undefined;
  speciesLoading: boolean;
  /** States or regions for the chosen country; empty when the country has no list. */
  subdivisions: Subdivision[];
  locale: string;
  /** The full address of this page, for "Copy link". */
  shareUrl: string;
}

const selectClass = 'field-input h-10 text-[14px]';
const labelClass = 'mb-1.5 text-[12px] font-medium text-ink-2';

function CopyLink({ url }: { url: string }) {
  const { t } = useTranslation();
  const [state, setState] = useState<'idle' | 'copied' | 'failed'>('idle');
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(url);
      setState('copied');
    } catch {
      setState('failed');
    }
    window.setTimeout(() => setState('idle'), 3000);
  };
  return (
    <div className="flex flex-wrap items-center gap-3">
      <Button variant="secondary" size="sm" onClick={() => void copy()}>
        {state === 'copied' ? (
          <Check size={15} aria-hidden="true" />
        ) : (
          <Link2 size={15} aria-hidden="true" />
        )}
        {t('treeAge.copyLink')}
      </Button>
      <span aria-live="polite" className="text-[12.5px] text-muted">
        {state === 'copied' && t('treeAge.linkCopied')}
        {state === 'failed' && t('treeAge.linkCopyFailed')}
      </span>
    </div>
  );
}

/** Everything the person tells us about their trees. Changes go straight to the address bar. */
export function InputsCard({
  inputs,
  onChange,
  species,
  speciesLoading,
  subdivisions,
  locale,
  shareUrl,
}: InputsCardProps) {
  const { t } = useTranslation();
  const countries = countryOptions(locale);
  const sortedSubdivisions = [...subdivisions].sort((a, b) => a.name.localeCompare(b.name, locale));
  const planning = inputs.age === 0;
  const speciesList = species ?? [];
  const speciesKnown = speciesList.some((s) => s.id === inputs.speciesId);

  const parseTrees = (text: string): DraftParse => {
    const checked = checkWholeNumber(text, TREES_MIN, TREES_MAX);
    return checked.ok
      ? checked
      : {
          ok: false,
          message: t(`treeAge.problem.${checked.problem}`, {
            min: TREES_MIN,
            max: new Intl.NumberFormat(locale).format(TREES_MAX),
          }),
        };
  };
  const parseGirth = (text: string): DraftParse => {
    const checked = checkGirth(text);
    return checked.ok
      ? checked
      : {
          ok: false,
          message: t(`treeAge.problem.${checked.problem}`, { min: GIRTH_MIN, max: GIRTH_MAX }),
        };
  };

  return (
    <section aria-label={t('treeAge.inputsTitle')} className="card flex flex-col gap-4 p-4 md:p-5">
      <h2 className="m-0 text-[18px]">{t('treeAge.inputsTitle')}</h2>

      <div className="flex flex-col">
        <label htmlFor="tree-age-country" className={labelClass}>
          {t('treeAge.country')}
        </label>
        <select
          id="tree-age-country"
          className={selectClass}
          value={inputs.country}
          onChange={(event) => onChange({ country: event.target.value })}
        >
          {countries.top.map((c) => (
            <option key={c.code} value={c.code}>
              {c.name}
            </option>
          ))}
          <optgroup label={t('treeAge.euGroup')}>
            {countries.eu.map((c) => (
              <option key={c.code} value={c.code}>
                {c.name}
              </option>
            ))}
          </optgroup>
        </select>
      </div>

      {sortedSubdivisions.length > 0 && (
        <div className="flex flex-col">
          <label htmlFor="tree-age-subdivision" className={labelClass}>
            {t('treeAge.subdivision')}
          </label>
          <select
            id="tree-age-subdivision"
            className={selectClass}
            value={inputs.subdivision ?? ''}
            onChange={(event) => onChange({ subdivision: event.target.value || null })}
          >
            <option value="">{t('treeAge.notSure')}</option>
            {sortedSubdivisions.map((s) => (
              <option key={s.code} value={s.code}>
                {s.name}
              </option>
            ))}
          </select>
        </div>
      )}

      <fieldset className="m-0 min-w-0 border-0 p-0">
        <legend className={`${labelClass} p-0`}>{t('treeAge.setting')}</legend>
        <div className="grid grid-cols-3 gap-2">
          {SETTING_CHOICES.map((choice) => {
            const Icon = SETTING_ICONS[choice];
            return (
              <label
                key={choice}
                className="relative flex cursor-pointer flex-col items-center gap-1.5 rounded-[12px] border border-line bg-surface px-1.5 py-3 text-center text-[13px] font-medium leading-tight text-ink-2 transition-colors hover:bg-ground has-[:checked]:border-forest has-[:checked]:bg-mint has-[:checked]:text-forest-deep has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-forest"
              >
                <input
                  type="radio"
                  name="tree-age-setting"
                  value={choice}
                  checked={inputs.setting === choice}
                  onChange={() => onChange({ setting: choice as TreeSetting })}
                  className="sr-only"
                />
                <Icon size={20} aria-hidden="true" />
                {t(`treeAge.settings.${choice}`)}
              </label>
            );
          })}
        </div>
      </fieldset>

      <div className="flex flex-col">
        <label htmlFor="tree-age-species" className={labelClass}>
          {t('treeAge.species')}
        </label>
        <select
          id="tree-age-species"
          className={selectClass}
          value={inputs.speciesId ?? ''}
          disabled={speciesLoading && speciesList.length === 0}
          onChange={(event) => onChange({ speciesId: event.target.value || null })}
        >
          {speciesList.length === 0 && (
            <option value={inputs.speciesId ?? ''}>
              {speciesLoading ? t('treeAge.speciesLoading') : t('treeAge.speciesNone')}
            </option>
          )}
          {inputs.speciesId && speciesList.length > 0 && !speciesKnown && (
            <option value={inputs.speciesId}>{inputs.speciesId}</option>
          )}
          {speciesList.map((s) => (
            <option key={s.id} value={s.id}>
              {s.common_name}
              {s.scientific_name ? ` (${s.scientific_name})` : ''}
            </option>
          ))}
        </select>
      </div>

      <AgeField age={inputs.age} onChange={(age) => onChange({ age })} />

      <NumberField
        id="tree-age-trees"
        label={t('treeAge.trees')}
        value={inputs.trees}
        unit={t('treeAge.treesUnit')}
        parse={parseTrees}
        onCommit={(value) => {
          if (value !== null) onChange({ trees: value });
        }}
      />

      <NumberField
        id="tree-age-girth"
        label={
          <>
            {t('treeAge.girth')}{' '}
            <span className="font-normal text-muted">· {t('treeAge.optional')}</span>
          </>
        }
        value={planning ? null : inputs.girthCm}
        unit={t('treeAge.girthUnit')}
        inputMode="decimal"
        disabled={planning}
        parse={parseGirth}
        onCommit={(value) => onChange({ girthCm: value })}
        hint={planning ? t('treeAge.girthNeedsAge') : t('treeAge.girthTip')}
      />

      <div className="border-t border-line pt-4">
        <CopyLink url={shareUrl} />
      </div>
    </section>
  );
}
