import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';
import { PageSpinner } from '@/components/ui/PageSpinner';
import { Pill } from '@/components/ui/StatusPill';
import { REGIONS } from '@/config/regions';
import { useSpecies } from '@/services/queries';

export default function SpeciesPage() {
  const { t } = useTranslation();
  const [region, setRegion] = useState<string>('');
  const { data, isLoading } = useSpecies(region || undefined);
  if (isLoading) return <PageSpinner />;
  const tone = (status: string) => (status === 'verified' ? 'mint' : status === 'pending' ? 'amber' : 'grey');
  return (
    <div className="flex flex-col gap-4 p-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="flex flex-col gap-1">
          <nav aria-label={t('app.breadcrumb')} className="flex items-center gap-2 text-[13px] text-muted">
            <Link to="/app/settings" className="text-ink-2 no-underline hover:text-forest">
              {t('nav.settings')}
            </Link>
            <span aria-hidden="true">›</span>
            <span className="font-semibold text-ink">{t('species.title')}</span>
          </nav>
          <h1 className="m-0 text-[24px]">{t('species.title')}</h1>
          <p className="m-0 max-w-[760px] text-sm text-ink-2">{t('species.subtitle')}</p>
        </div>
        <label className="text-[13px] text-ink-2">
          {t('species.regions')}{' '}
          <select value={region} onChange={(e) => setRegion(e.target.value)} className="field-input ml-2 h-9 w-auto">
            <option value="">{t('species.filterAll')}</option>
            {REGIONS.map((r) => (
              <option key={r.id} value={r.id}>
                {t(`country.${r.id}`)}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {(data ?? []).map((s) => (
          <article key={s.id} className="card flex flex-col gap-2.5 p-5">
            <div className="flex items-start justify-between gap-2">
              <div>
                <h2 className="m-0 text-[17px]">{s.common_name}</h2>
                <span className="text-[13px] italic text-ink-2">{s.scientific_name}</span>
              </div>
              <span className="rounded-[6px] bg-ground px-2 py-1 font-mono text-[11px] text-ink-2">{s.regions.join(' · ')}</span>
            </div>
            <span className="text-[12px] text-muted">{t('species.group')}: {s.group.replace(/_/g, ' ')}</span>
            <dl className="m-0 grid grid-cols-2 gap-x-3 gap-y-1.5 text-[13px]">
              <dt className="text-muted">{t('species.referenceDensity')}</dt>
              <dd className="m-0 font-mono">{s.reference_density_per_ha.value}{t('species.perHa')}</dd>
              <dt className="text-muted">{t('species.maxDensity')}</dt>
              <dd className="m-0 font-mono">{s.max_density_per_ha}{t('species.perHa')}</dd>
              <dt className="text-muted">{t('species.maturity')}</dt>
              <dd className="m-0 font-mono">{s.maturity_years} {t('species.years')}</dd>
              <dt className="text-muted">{t('species.woodDensity')}</dt>
              <dd className="m-0 flex items-center gap-2 font-mono">
                {s.wood_density_g_cm3.value} g/cm³ <Pill tone={tone(s.wood_density_g_cm3.verification_status)}>{t(`species.status_${s.wood_density_g_cm3.verification_status}`, { defaultValue: s.wood_density_g_cm3.verification_status })}</Pill>
              </dd>
            </dl>
            <div className="flex flex-wrap gap-1.5">
              {s.suitable_climate_zones.map((z) => (
                <span key={z} className="rounded-full bg-ground px-2 py-0.5 text-[11px] text-ink-2">{z.replace(/_/g, ' ')}</span>
              ))}
            </div>
            {s.notes && <p className="m-0 text-[12px] text-muted">{s.notes}</p>}
          </article>
        ))}
      </div>
    </div>
  );
}
