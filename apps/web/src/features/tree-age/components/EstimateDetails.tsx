import { useTranslation } from 'react-i18next';
import { formatCarbon } from '../logic/treeAgeLogic';
import type { TreeAgeAssessment } from '../types';
import { Disclosure } from './Disclosure';

interface EstimateDetailsProps {
  assessment: TreeAgeAssessment;
  locale: string;
}

/** For the curious: which method, which climate, how sure, and what still needs checking. */
export function EstimateDetails({ assessment, locale }: EstimateDetailsProps) {
  const { t } = useTranslation();
  const { carbon } = assessment;
  const pending = carbon.parameters_used.filter((p) => p.verification_status !== 'verified');
  const measured = carbon.method === 'tier2-girth';
  const climate = [
    assessment.climate_zone_label ?? assessment.climate_zone,
    assessment.climate_zone_source,
  ]
    .filter(Boolean)
    .join(' · ');
  const perTree = carbon.per_tree;

  const rows: [string, string][] = [
    [
      t('treeAge.details.method'),
      measured ? t('treeAge.details.methodGirth') : t('treeAge.details.methodAge'),
    ],
  ];
  if (carbon.confidence) {
    rows.push([
      t('treeAge.details.confidence'),
      t(`treeAge.details.confidenceLevel.${carbon.confidence}`, {
        defaultValue: carbon.confidence,
      }),
    ]);
  }
  if (climate) rows.push([t('treeAge.details.climate'), climate]);
  if (perTree.stored_now_kg_co2e !== null && perTree.annual_now_kg_co2e !== null) {
    rows.push([
      t('treeAge.details.perTree'),
      t('treeAge.details.perTreeValue', {
        stored: formatCarbon(perTree.stored_now_kg_co2e, locale),
        annual: formatCarbon(perTree.annual_now_kg_co2e, locale),
      }),
    ]);
  }
  if (carbon.parameters_used.length > 0) {
    rows.push([
      t('treeAge.details.parameters'),
      pending.length > 0
        ? t('treeAge.details.parametersPending', {
            count: carbon.parameters_used.length,
            pending: pending.length,
          })
        : t('treeAge.details.parametersAllVerified', { count: carbon.parameters_used.length }),
    ]);
  }

  return (
    <div className="card px-4 py-2 md:px-5">
      <Disclosure label={t('treeAge.details.title')}>
        <div className="flex flex-col gap-3 pb-2">
          <dl className="m-0 grid grid-cols-1 gap-x-6 gap-y-1 text-[13.5px] sm:grid-cols-[160px_minmax(0,1fr)] sm:gap-y-2.5">
            {rows.map(([term, value]) => (
              <div key={term} className="contents">
                <dt className="font-semibold text-ink sm:pt-px">{term}</dt>
                <dd className="m-0 mb-1.5 text-ink-2 sm:mb-0">{value}</dd>
              </div>
            ))}
          </dl>
          {carbon.notes.length > 0 && (
            <ul className="m-0 flex list-disc flex-col gap-1 pl-5 text-[13px] leading-snug text-ink-2">
              {carbon.notes.map((note) => (
                <li key={note}>{note}</li>
              ))}
            </ul>
          )}
        </div>
      </Disclosure>
    </div>
  );
}
