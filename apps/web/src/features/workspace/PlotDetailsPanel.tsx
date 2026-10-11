import { useState } from 'react';
import {
  Calendar,
  ChevronRight,
  Info,
  Leaf,
  Plus,
  ShieldCheck,
  Sprout,
  TreePine,
  Vegan,
  Wind,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';
import { buttonClass } from '@/components/ui/buttonStyles';
import { Field, UnitInput } from '@/components/ui/Field';
import { InfoButton } from '@/components/ui/InfoButton';
import { formatArea, formatNumber, formatRange, unitLabel } from '@/lib/format';
import { isApproximate } from '@/lib/landInput';
import { useUiStore } from '@/store/uiStore';
import type { Analysis, CarbonEstimate, Plot, Species } from '@/types/api';
import { summarize, type TreeForm } from './logic/workspaceModel';

interface Props {
  plots: Plot[];
  plot: Plot | null;
  species: Species[];
  form: TreeForm;
  onForm: (form: TreeForm) => void;
  estimate?: CarbonEstimate;
  analysis?: Analysis;
  saving: boolean;
  updating: boolean;
  locale: string;
  onSelectPlot: (id: string) => void;
}

export function PlotDetailsPanel({
  plots,
  plot,
  species,
  form,
  onForm,
  estimate,
  analysis,
  saving,
  updating,
  locale,
  onSelectPlot,
}: Props) {
  const { t } = useTranslation();
  const areaUnit = useUiStore((s) => s.areaUnit);
  const setLandInputMode = useUiStore((s) => s.setLandInputMode);
  const [showMeasurements, setShowMeasurements] = useState(
    Boolean(form.average_dbh_cm || form.average_height_m),
  );
  const summary = summarize(estimate, analysis);
  const currentYear = new Date().getFullYear();

  if (!plot) {
    return (
      <aside
        aria-label={t('panel.title')}
        className="card flex flex-col gap-3 p-4 text-sm text-muted"
      >
        <h2 className="text-[17px] text-ink">{t('panel.title')}</h2>
        {t('panel.noPlot')}
      </aside>
    );
  }

  const area = formatArea(plot.area_hectares, plot.country, locale, areaUnit);
  const years = Array.from({ length: 31 }, (_, i) => currentYear - i);
  const infoIcon = <span className="text-forest">●</span>;

  return (
    <aside aria-label={t('panel.title')} className="card flex flex-col gap-3.5 p-4">
      <div className="flex flex-col gap-2">
        <h2 className="m-0 flex items-center gap-2 whitespace-nowrap text-[16px]">
          <TreePine size={20} className="shrink-0 text-forest" aria-hidden="true" />
          {t('panel.title')}
        </h2>
        <label className="block w-full text-[13px]">
          <span className="sr-only">{t('panel.plotSelector')}</span>
          <select
            value={plot.plot_id}
            onChange={(e) => onSelectPlot(e.target.value)}
            className="field-input h-10 w-full max-w-full truncate font-semibold"
          >
            {plots.map((p) => (
              <option key={p.plot_id} value={p.plot_id}>
                {p.name}
              </option>
            ))}
          </select>
        </label>
        {isApproximate(plot) && (
          <p className="m-0 flex items-start gap-2 rounded-[10px] bg-blue-tint px-3 py-2 text-[12px] leading-snug text-blue-text">
            <Info size={14} className="mt-[1px] shrink-0" aria-hidden="true" />
            <span>
              {t('panel.approximateNote')}{' '}
              <button
                type="button"
                onClick={() => setLandInputMode('edit')}
                className="font-semibold underline underline-offset-2"
              >
                {t('panel.drawExactEdges')}
              </button>
            </span>
          </p>
        )}
      </div>

      <form className="flex flex-col gap-3" onSubmit={(e) => e.preventDefault()}>
        <Field
          id="area"
          inline
          label={t('panel.landArea')}
          icon={<Vegan size={16} className="text-forest" aria-hidden="true" />}
        >
          <UnitInput unit={t(area.primaryUnit === 'hectare' ? 'units.hectares' : 'units.acres')}>
            <input
              id="area"
              readOnly
              value={formatNumber(area.primaryValue, locale, { maximumFractionDigits: 2 })}
              className="h-10 w-full min-w-0 bg-ground px-3 text-sm text-ink-2"
            />
          </UnitInput>
        </Field>
        <Field
          id="tree-count"
          inline
          label={t('panel.numberOfTrees')}
          icon={<TreePine size={16} className="text-forest" aria-hidden="true" />}
        >
          <UnitInput unit={t('units.trees')}>
            <input
              id="tree-count"
              type="number"
              min={1}
              step={1}
              value={form.tree_count}
              onChange={(e) =>
                onForm({ ...form, tree_count: Math.max(0, Math.round(Number(e.target.value))) })
              }
              className="h-10 w-full min-w-0 px-3 text-sm outline-none"
            />
          </UnitInput>
        </Field>
        <Field
          id="species"
          inline
          label={t('panel.treeType')}
          icon={<Leaf size={16} className="text-forest" aria-hidden="true" />}
        >
          <select
            id="species"
            value={form.species_id}
            onChange={(e) => onForm({ ...form, species_id: e.target.value })}
            className="field-input h-10"
          >
            {species.map((s) => (
              <option key={s.id} value={s.id}>
                {s.common_name} — {s.scientific_name}
              </option>
            ))}
            {species.length === 0 && <option value={form.species_id}>{form.species_id}</option>}
          </select>
        </Field>
        <Field
          id="plantation-year"
          inline
          label={t('panel.plantationYear')}
          icon={<Calendar size={16} className="text-forest" aria-hidden="true" />}
        >
          <select
            id="plantation-year"
            value={form.plantation_year}
            onChange={(e) => onForm({ ...form, plantation_year: Number(e.target.value) })}
            className="field-input h-10"
          >
            {years.map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </select>
        </Field>
        {!showMeasurements ? (
          <button
            type="button"
            onClick={() => setShowMeasurements(true)}
            className="flex h-10 items-center justify-between rounded-[10px] border border-dashed border-line px-3 text-[13px] text-ink-2 hover:bg-ground"
          >
            {t('panel.measurementsToggle')}
            <Plus size={16} aria-hidden="true" />
          </button>
        ) : (
          <div className="grid grid-cols-2 gap-2.5 rounded-[10px] border border-line bg-ground p-2.5">
            <Field id="dbh" label={t('panel.averageDbh')}>
              <input
                id="dbh"
                type="number"
                min={0}
                step={0.5}
                placeholder="—"
                value={form.average_dbh_cm ?? ''}
                onChange={(e) =>
                  onForm({
                    ...form,
                    average_dbh_cm: e.target.value === '' ? null : Number(e.target.value),
                  })
                }
                className="field-input"
              />
            </Field>
            <Field id="height" label={t('panel.averageHeight')}>
              <input
                id="height"
                type="number"
                min={0}
                step={0.5}
                placeholder="—"
                value={form.average_height_m ?? ''}
                onChange={(e) =>
                  onForm({
                    ...form,
                    average_height_m: e.target.value === '' ? null : Number(e.target.value),
                  })
                }
                className="field-input"
              />
            </Field>
          </div>
        )}
        <p className="m-0 min-h-[16px] text-[12px] text-muted" aria-live="polite">
          {saving ? t('panel.savingTrees') : updating ? t('panel.updating') : ''}
        </p>
      </form>

      <hr className="m-0 border-0 border-t border-line" />

      <dl className="m-0 flex flex-col gap-3">
        <div className="flex items-center justify-between gap-2">
          <dt className="flex items-center gap-2 text-sm text-ink-2">
            <Wind size={16} className="text-forest" aria-hidden="true" />
            {t('panel.removalRange')}
          </dt>
          <dd className="m-0 flex items-baseline gap-1.5">
            <span className="big-number text-[20px]">
              {summary.removal ? formatRange(summary.removal, locale, 1) : '—'}
            </span>
            <span className="text-[12px] text-muted">
              {summary.removal ? unitLabel(summary.removal.unit) : ''}
            </span>
            <InfoButton label={t('panel.whatIsThis')} text={t('panel.removalInfo')} />
          </dd>
        </div>
        <div className="flex items-center justify-between gap-2">
          <dt className="flex items-center gap-2 text-sm text-ink-2">
            <Sprout size={16} className="text-forest" aria-hidden="true" />
            {t('panel.vegetationHealth')}
          </dt>
          <dd className="m-0 flex items-baseline gap-1.5">
            <span className="big-number text-[20px]">
              {summary.ndvi != null ? summary.ndvi.toFixed(2) : '—'}
            </span>
            <span className="text-[12px] font-semibold text-forest">
              {summary.ndviClass ? t(`ndvi.${summary.ndviClass}`) : ''}
            </span>
            <InfoButton label={t('panel.whatIsThis')} text={t('panel.vegetationInfo')} />
          </dd>
        </div>
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center justify-between gap-2">
            <dt className="flex items-center gap-2 text-sm text-ink-2">
              <ShieldCheck size={16} className="text-forest" aria-hidden="true" />
              {t('panel.readiness')}
            </dt>
            <dd className="m-0 flex items-baseline gap-1.5">
              <span className="big-number text-[20px]">{summary.readinessScore ?? '—'}</span>
              <span className="text-[12px] text-muted">
                / 100
                {summary.readinessGrade ? ` · ${t(`confidence.${summary.readinessGrade}`)}` : ''}
              </span>
              <InfoButton label={t('panel.whatIsThis')} text={t('panel.readinessInfo')} />
            </dd>
          </div>
          <span className="block h-2 overflow-hidden rounded-full bg-[#E3E9E4]" aria-hidden="true">
            <span
              className="block h-full bg-forest transition-[width]"
              style={{ width: `${summary.readinessScore ?? 0}%` }}
            />
          </span>
          {summary.missing.length > 0 && (
            <span className="text-[12px] text-ink-2">
              {t('panel.missing', { items: summary.missing.slice(0, 3).join(' · ') })}
            </span>
          )}
        </div>
      </dl>

      <Link
        to={`/app/plots/${plot.plot_id}/results`}
        className={buttonClass('primary', 'lg', 'w-full')}
      >
        {infoIcon}
        {t('panel.seeCarbonPotential')}
        <ChevronRight size={16} aria-hidden="true" />
      </Link>
      <p className="m-0 text-[12px] leading-relaxed text-muted">{t('panel.note')}</p>
    </aside>
  );
}
