import { ExternalLink, Satellite } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Pill } from '@/components/ui/StatusPill';
import { hasSatelliteOverride } from '@/config/mapEnv';
import { errorMessage } from '@/lib/errors';
import { countryName } from '@/lib/format';
import { chooseProvider, coversCountry, imageryCountry, termsStatus } from '@/lib/imagery';
import { useImageryProviders, usePlots } from '@/services/queries';
import { useUiStore } from '@/store/uiStore';

const TERMS_TONE = { yes: 'mint', no: 'amber', check: 'grey' } as const;

/** Settings → Map imagery: pick the satellite provider for the current country, with licence and analysis terms. */
export function ImagerySettings() {
  const { t } = useTranslation();
  const language = useUiStore((s) => s.language);
  const country = useUiStore((s) => s.country);
  const selectedPlotId = useUiStore((s) => s.selectedPlotId);
  const imageryChoice = useUiStore((s) => s.imageryChoice);
  const setImageryChoice = useUiStore((s) => s.setImageryChoice);
  const plots = usePlots().data?.items ?? [];
  const plotCountry = plots.find((p) => p.plot_id === selectedPlotId)?.country;
  const key = imageryCountry(plotCountry, country);
  const storeKey = key ?? 'default';
  const query = useImageryProviders(key);
  const active = chooseProvider(query.data, imageryChoice[storeKey]);
  const providers = [...(query.data?.providers ?? [])].sort(
    (a, b) => Number(b.available) - Number(a.available),
  );
  const place = key ? countryName(key, language) : t('settings.imageryDefaultRegion');

  return (
    <section aria-labelledby="imagery-title" className="card flex flex-col gap-3 p-5">
      <div className="flex flex-col gap-1">
        <h2 id="imagery-title" className="m-0 flex items-center gap-2 text-[16px]">
          <Satellite size={18} className="text-forest" aria-hidden="true" />
          {t('settings.imageryTitle')}
        </h2>
        <p className="m-0 text-[13px] text-ink-2">{t('settings.imageryIntro', { place })}</p>
      </div>
      {hasSatelliteOverride && (
        <p className="m-0 rounded-[10px] bg-blue-tint px-3 py-2 text-[12px] text-blue-text">
          {t('settings.imageryEnvOverride')}
        </p>
      )}
      {query.isLoading && <span className="skeleton block h-24 w-full" />}
      {query.error != null && (
        <p role="alert" className="m-0 text-[13px] text-amber-text">
          {errorMessage(query.error, t)}
        </p>
      )}
      {providers.length > 0 && (
        <fieldset className="m-0 flex flex-col gap-2 border-0 p-0">
          <legend className="sr-only">{t('settings.imageryTitle')}</legend>
          {providers.map((p) => {
            const analysis = termsStatus(p.analysis_allowed);
            const checked = active?.id === p.id;
            return (
              <label
                key={p.id}
                className={`flex items-start gap-3 rounded-[12px] border px-3.5 py-3 text-sm ${p.available ? 'cursor-pointer' : 'opacity-60'} ${checked ? 'border-forest bg-mint' : 'border-line'}`}
              >
                <input
                  type="radio"
                  name="imagery-provider"
                  className="mt-1 h-4 w-4 shrink-0 accent-forest"
                  checked={checked}
                  disabled={!p.available}
                  onChange={() =>
                    setImageryChoice(storeKey, p.id === query.data?.recommended ? null : p.id)
                  }
                />
                <span className="flex min-w-0 flex-1 flex-col gap-1">
                  <span className="flex flex-wrap items-center gap-2">
                    <span className="font-semibold text-ink">{p.name}</span>
                    {p.id === query.data?.recommended && (
                      <Pill tone="mint">{t('settings.imageryRecommended')}</Pill>
                    )}
                    {!coversCountry(p, key) && (
                      <Pill tone="grey">{t('settings.imageryOtherCoverage')}</Pill>
                    )}
                  </span>
                  {p.resolution && <span className="text-[12px] text-muted">{p.resolution}</span>}
                  <span className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[12px] text-ink-2">
                    <span>
                      {t('settings.imageryLicence')}:{' '}
                      {p.license_url ? (
                        <a
                          href={p.license_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 font-medium text-forest"
                        >
                          {p.license}
                          <ExternalLink size={11} aria-hidden="true" />
                        </a>
                      ) : (
                        p.license
                      )}
                    </span>
                    <span className="flex items-center gap-1.5">
                      {t('settings.imageryAnalysis')}:{' '}
                      <Pill tone={TERMS_TONE[analysis]}>{t(`settings.analysis_${analysis}`)}</Pill>
                    </span>
                  </span>
                  {!p.available && p.unavailable_reason && (
                    <span className="text-[12px] text-amber-text">
                      {t('settings.imageryUnavailable', { reason: p.unavailable_reason })}
                    </span>
                  )}
                </span>
              </label>
            );
          })}
        </fieldset>
      )}
      {query.data?.notes && <p className="m-0 text-[12px] text-muted">{query.data.notes}</p>}
    </section>
  );
}
