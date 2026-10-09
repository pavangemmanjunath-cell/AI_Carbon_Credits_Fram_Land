import './i18n';
import { useMemo } from 'react';
import { LoaderCircle, Sprout } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Link, useLocation } from 'react-router';
import { intlLocale } from '@/lib/format';
import { useSpecies } from '@/services/queries';
import { useTreeAgeAssessment, useTreeAgeRules } from '@/services/treeAgeApi';
import { useUiStore } from '@/store/uiStore';
import { CarbonCurveChart } from './components/CarbonCurveChart';
import { CreditOutlook } from './components/CreditOutlook';
import { ErrorNotice } from './components/ErrorNotice';
import { EstimateDetails } from './components/EstimateDetails';
import { HeadlineCards } from './components/HeadlineCards';
import { InputsCard } from './components/InputsCard';
import { RulesSection } from './components/RulesSection';
import {
  DEBOUNCE_MS,
  buildRequestBody,
  regionName,
  requestKey,
  resolveSpeciesId,
  resolveSubdivision,
  toSearchParams,
} from './logic/treeAgeLogic';
import type { TreeAgeInputs, TreeAgeRequestBody } from './types';
import { useDebouncedValue } from './useDebouncedValue';
import { useTreeAgeUrl } from './useTreeAgeUrl';

function ResultsSkeleton({ label }: { label: string }) {
  return (
    <div role="status" aria-label={label} className="flex flex-col gap-4">
      <div className="grid grid-cols-1 gap-3 md:grid-cols-3" aria-hidden="true">
        {[0, 1, 2].map((i) => (
          <span key={i} className="skeleton h-[132px] rounded-[12px]" />
        ))}
      </div>
      <span className="skeleton h-[380px] rounded-[12px]" aria-hidden="true" />
      <span className="skeleton h-[84px] rounded-[12px]" aria-hidden="true" />
    </div>
  );
}

export default function TreeAgePage() {
  const { t, i18n } = useTranslation();
  const location = useLocation();
  const language = useUiStore((s) => s.language);
  const { wanted, commit } = useTreeAgeUrl();

  // ── Lists that depend on the country ──────────────────────────────────────
  const speciesQuery = useSpecies(wanted.country);
  const rulesQuery = useTreeAgeRules(wanted.country);
  const species = speciesQuery.data;
  const subdivisions = rulesQuery.data?.subdivisions;

  // What the person sees: the address bar, with the species and the state checked against the
  // lists the API gave for this country.
  const inputs: TreeAgeInputs = useMemo(
    () => ({
      ...wanted,
      speciesId: resolveSpeciesId(wanted.speciesId, species),
      subdivision: resolveSubdivision(wanted.subdivision, subdivisions),
    }),
    [wanted, species, subdivisions],
  );
  const change = (patch: Partial<TreeAgeInputs>) => commit(patch, inputs);

  // ── The request: wait for the lists, then wait for the slider to settle ──
  // A state named in a hand-edited link is checked against the API's list before it is sent, so
  // a wrong code never turns into an error message.
  const speciesSettled = species !== undefined || speciesQuery.isError;
  const rulesSettled = rulesQuery.isSuccess || rulesQuery.isError;
  const ready = speciesSettled && (wanted.subdivision === null || rulesSettled);
  const body = ready ? buildRequestBody(inputs) : null;
  const key = requestKey(body);
  const settledKey = useDebouncedValue(key, DEBOUNCE_MS);
  const activeKey = settledKey ?? key;
  const activeBody = useMemo(
    () => (activeKey ? (JSON.parse(activeKey) as TreeAgeRequestBody) : null),
    [activeKey],
  );
  const assessmentQuery = useTreeAgeAssessment(activeBody);
  const assessment = assessmentQuery.data;
  const settling = key !== activeKey;
  const updating =
    assessment !== undefined &&
    (settling || assessmentQuery.isFetching || assessmentQuery.isPlaceholderData);

  // ── What the results are about (not what is being typed right now) ────────
  const shownAge = assessment?.inputs.age_years ?? inputs.age;
  const locale = intlLocale(language, assessment?.inputs.country ?? inputs.country);
  const english = (i18n.resolvedLanguage ?? i18n.language ?? 'en').startsWith('en');
  const disclaimer =
    english && assessment?.disclaimer ? assessment.disclaimer : t('treeAge.disclaimer');
  const regionLabel = regionName(assessment?.inputs.region ?? inputs.country, locale);
  const noSpecies = speciesQuery.isSuccess && (species?.length ?? 0) === 0 && !inputs.speciesId;
  const shareUrl = `${window.location.origin}${location.pathname}?${toSearchParams(inputs).toString()}`;

  return (
    <div className="mx-auto flex max-w-[1440px] flex-col gap-5 p-4 md:p-5">
      <header className="flex max-w-[820px] flex-col gap-1.5">
        <nav
          aria-label={t('treeAge.breadcrumbLabel')}
          className="flex items-center gap-2 text-[13px] text-muted"
        >
          <Link to="/app" className="text-ink-2 no-underline hover:text-forest">
            {t('treeAge.breadcrumbWorkspace')}
          </Link>
          <span aria-hidden="true">›</span>
          <span className="font-semibold text-ink">{t('treeAge.title')}</span>
        </nav>
        <h1 className="m-0 text-[28px] tracking-tight">{t('treeAge.title')}</h1>
        <p className="m-0 text-sm text-ink-2">{t('treeAge.subtitle')}</p>
      </header>

      <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-[360px_minmax(0,1fr)] xl:grid-cols-[380px_minmax(0,1fr)]">
        <div className="lg:sticky lg:top-4 lg:max-h-[calc(100vh-2rem)] lg:overflow-y-auto lg:rounded-[12px]">
          <InputsCard
            inputs={inputs}
            onChange={change}
            species={species}
            speciesLoading={speciesQuery.isPending}
            subdivisions={subdivisions ?? []}
            locale={locale}
            shareUrl={shareUrl}
          />
        </div>

        <div className="relative flex min-w-0 flex-col gap-4">
          {/* Always in the page, so screen readers hear "Updating…"; a small chip on the top
              edge of the results for everyone else, so nothing below it moves. */}
          <p
            role="status"
            className={
              updating
                ? 'pointer-events-none absolute right-4 top-0 z-10 m-0 flex -translate-y-1/2 items-center gap-1.5 rounded-full border border-line bg-surface px-3 py-1 text-[12.5px] font-medium text-ink-2 shadow-sm'
                : 'sr-only'
            }
          >
            {updating && (
              <>
                <LoaderCircle size={14} aria-hidden="true" className="animate-spin" />
                {t('treeAge.updating')}
              </>
            )}
          </p>

          {assessmentQuery.isError && (
            <ErrorNotice
              error={assessmentQuery.error}
              onRetry={() => void assessmentQuery.refetch()}
            />
          )}
          {!assessmentQuery.isError && speciesQuery.isError && (
            <ErrorNotice error={speciesQuery.error} onRetry={() => void speciesQuery.refetch()} />
          )}

          {noSpecies && (
            <p className="card m-0 p-4 text-[14px] text-ink-2">{t('treeAge.noSpecies')}</p>
          )}

          {assessment && !assessmentQuery.isError ? (
            <>
              <HeadlineCards
                stored={assessment.carbon.stored_now}
                annual={assessment.carbon.annual_now}
                ageClass={assessment.age_class}
                ageClasses={rulesQuery.data?.age_classes}
                locale={locale}
                updating={updating}
              />

              {shownAge === 0 && (
                <p className="m-0 flex items-start gap-2.5 rounded-[12px] bg-mint px-4 py-3 text-[13.5px] leading-snug text-forest-deep">
                  <Sprout size={17} aria-hidden="true" className="mt-px shrink-0" />
                  {t('treeAge.planningNote')}
                </p>
              )}

              <CarbonCurveChart
                curve={assessment.carbon.curve}
                age={shownAge}
                storedNow={assessment.carbon.stored_now}
                method={assessment.carbon.method}
                locale={locale}
                updating={updating}
              />

              <EstimateDetails assessment={assessment} locale={locale} />

              <CreditOutlook outlook={assessment.credit_outlook} age={shownAge} />

              <RulesSection
                rules={assessment.rules}
                regionLabel={regionLabel}
                locale={locale}
                disclaimer={disclaimer}
              />
            </>
          ) : (
            !assessmentQuery.isError &&
            !speciesQuery.isError &&
            !noSpecies && <ResultsSkeleton label={t('treeAge.loadingResults')} />
          )}
        </div>
      </div>
    </div>
  );
}
