import { useState } from 'react';
import { Copy, Lock, Sprout } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';
import { buttonClass } from '@/components/ui/buttonStyles';
import { copyToClipboard } from '@/lib/download';
import { formatNumber } from '@/lib/format';
import { perimeterMetres } from '@/lib/geo';
import type { Plot, Species } from '@/types/api';
import { corners, cornersText, simulateLink, treesThatFit } from './lockedLand';
import './lockedLand.i18n';

const SIMULATION_MAX_TREES = 2000;

interface Props {
  plot: Plot | null | undefined;
  species: Species[];
  defaultSpeciesId: string;
  locale: string;
}

/** The saved ("locked") boundary: every corner's latitude and longitude, its size, and how many trees fit. */
export function LockedLandCard({ plot, species, defaultSpeciesId, locale }: Props) {
  const { t } = useTranslation();
  const [speciesId, setSpeciesId] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  if (!plot?.geometry) return null;

  const list = corners(plot.geometry);
  const chosenId =
    speciesId ??
    (species.some((s) => s.id === defaultSpeciesId) ? defaultSpeciesId : (species[0]?.id ?? ''));
  const chosen = species.find((s) => s.id === chosenId);
  const fit = treesThatFit(plot.area_hectares, chosen);
  const trees = fit.trees === null ? null : Math.min(fit.trees, SIMULATION_MAX_TREES);
  const n = (v: number, digits = 2) => formatNumber(v, locale, { maximumFractionDigits: digits });

  const copy = async () => {
    setCopied(await copyToClipboard(cornersText(list)));
    window.setTimeout(() => setCopied(false), 2000);
  };

  return (
    <section className="card flex flex-col gap-3 p-4" aria-labelledby="locked-land-title">
      <div className="flex items-start gap-2.5">
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-mint text-forest-deep">
          <Lock size={15} aria-hidden="true" />
        </span>
        <div className="flex min-w-0 flex-col gap-0.5">
          <h2 id="locked-land-title" className="m-0 text-[15px]">
            {t('lockedLand.title')}
          </h2>
          <p className="m-0 text-[12px] text-ink-2">{t('lockedLand.subtitle')}</p>
        </div>
      </div>

      <dl className="m-0 grid grid-cols-3 gap-2 text-[12px]">
        {[
          [t('lockedLand.area'), `${n(plot.area_hectares)} ha`],
          [t('lockedLand.perimeter'), `${n(perimeterMetres(plot.geometry), 0)} m`],
          [t('lockedLand.corners'), String(list.length)],
        ].map(([label, value]) => (
          <div key={label} className="rounded-[10px] bg-ground px-2.5 py-2">
            <dt className="text-ink-2">{label}</dt>
            <dd className="m-0 font-mono text-[14px] font-semibold text-ink">{value}</dd>
          </div>
        ))}
      </dl>

      <div className="max-h-[180px] overflow-auto rounded-[10px] border border-line">
        <table className="w-full border-collapse text-[12px]">
          <thead className="sticky top-0 bg-surface">
            <tr className="text-left text-[11px] text-muted">
              <th className="border-b border-line px-2.5 py-1.5 font-medium">#</th>
              <th className="border-b border-line px-2.5 py-1.5 text-right font-medium">
                {t('lockedLand.lat')}
              </th>
              <th className="border-b border-line px-2.5 py-1.5 text-right font-medium">
                {t('lockedLand.lon')}
              </th>
            </tr>
          </thead>
          <tbody>
            {list.map((c, i) => (
              <tr key={i} className="border-b border-line last:border-0">
                <td className="px-2.5 py-1 text-muted">{i + 1}</td>
                <td className="px-2.5 py-1 text-right font-mono tabular-nums">
                  {c.lat.toFixed(6)}
                </td>
                <td className="px-2.5 py-1 text-right font-mono tabular-nums">
                  {c.lon.toFixed(6)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <button
        type="button"
        onClick={() => void copy()}
        className={`${buttonClass('secondary', 'sm')} self-start`}
      >
        <Copy size={14} aria-hidden="true" />{' '}
        {copied ? t('lockedLand.copied') : t('lockedLand.copy')}
      </button>

      <label className="flex flex-col gap-1 text-[12px] text-ink-2">
        {t('lockedLand.species')}
        <select
          className="field-input h-10"
          value={chosenId}
          onChange={(e) => setSpeciesId(e.target.value)}
        >
          {species.map((s) => (
            <option key={s.id} value={s.id}>
              {s.common_name} — {s.scientific_name}
            </option>
          ))}
        </select>
      </label>

      {fit.trees === null ? (
        <p className="m-0 text-[12.5px] text-amber-text">{t('lockedLand.noDensity')}</p>
      ) : (
        <div className="flex flex-col gap-1 rounded-[10px] bg-mint/60 px-3 py-2.5">
          <span className="flex items-center gap-2 text-[14px] font-semibold text-forest-deep">
            <Sprout size={16} aria-hidden="true" />
            {t('lockedLand.fit', { count: fit.trees, spacing: n(fit.spacingM ?? 0, 1) })}
          </span>
          <span className="text-[11.5px] text-ink-2">
            {t('lockedLand.fitSource', {
              density: n(fit.densityPerHa ?? 0, 0),
              source: fit.source,
              status: fit.status,
            })}
          </span>
          {fit.trees > SIMULATION_MAX_TREES && (
            <span className="text-[11.5px] text-amber-text">{t('lockedLand.capped')}</span>
          )}
        </div>
      )}

      {trees !== null && trees > 0 && (
        <Link
          to={simulateLink(plot, chosenId, trees, new Date().getFullYear())}
          className={`${buttonClass('primary', 'md')} justify-center`}
        >
          {t('lockedLand.simulate')}
        </Link>
      )}
    </section>
  );
}
