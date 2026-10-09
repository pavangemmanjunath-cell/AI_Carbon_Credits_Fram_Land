import { useTranslation } from 'react-i18next';
import { splitRules } from '../logic/treeAgeLogic';
import type { TreeAgeRule } from '../types';
import { Disclosure } from './Disclosure';
import { RuleCard } from './RuleCard';

interface RulesSectionProps {
  rules: TreeAgeRule[];
  /** "India", "the European Union": the place the other rules were checked for. */
  regionLabel: string;
  locale: string;
  /** The API's own disclaimer, shown at the bottom exactly as written. */
  disclaimer: string;
}

/** Rules that apply first; the rest (with their reasons) are one click away. */
export function RulesSection({ rules, regionLabel, locale, disclaimer }: RulesSectionProps) {
  const { t } = useTranslation();
  const { applying, other } = splitRules(rules);

  return (
    <section aria-labelledby="tree-age-rules-title" className="flex flex-col gap-3">
      <div className="flex flex-col gap-1">
        <h2 id="tree-age-rules-title" className="m-0 text-[18px]">
          {t('treeAge.rulesTitle')}
        </h2>
        <p className="m-0 text-[13.5px] text-ink-2">{t('treeAge.rulesSubtitle')}</p>
      </div>

      {applying.length > 0 ? (
        <ul className="m-0 flex list-none flex-col gap-3 p-0">
          {applying.map((rule) => (
            <li key={rule.id}>
              <RuleCard rule={rule} locale={locale} />
            </li>
          ))}
        </ul>
      ) : (
        <p className="card m-0 p-4 text-[14px] text-ink-2">{t('treeAge.noApplyingRules')}</p>
      )}

      {other.length > 0 && (
        <div className="card px-4 py-2">
          <Disclosure
            label={t('treeAge.otherRules', { region: regionLabel })}
            meta={`(${other.length})`}
          >
            <ul className="m-0 flex list-none flex-col gap-3 p-0 pb-2">
              {other.map((rule) => (
                <li key={rule.id}>
                  <RuleCard rule={rule} locale={locale} muted />
                </li>
              ))}
            </ul>
          </Disclosure>
        </div>
      )}

      {disclaimer && <p className="m-0 text-[12.5px] leading-relaxed text-muted">{disclaimer}</p>}
    </section>
  );
}
