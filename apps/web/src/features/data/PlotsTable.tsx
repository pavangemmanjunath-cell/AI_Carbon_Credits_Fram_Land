import { ChartColumn, MapPinned, Trash2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate } from 'react-router';
import { Button } from '@/components/ui/Button';
import { buttonClass } from '@/components/ui/buttonStyles';
import { PageSpinner } from '@/components/ui/PageSpinner';
import { Pill } from '@/components/ui/StatusPill';
import { formatArea, formatDate, intlLocale } from '@/lib/format';
import { isApproximate } from '@/lib/landInput';
import { useDeletePlot } from '@/services/queries';
import { useUiStore } from '@/store/uiStore';
import type { Plot } from '@/types/api';
import { plotSourceKey } from './logic/dataModel';

/** "Land plots" tab — the former My plots list. */
export function PlotsTable({ plots, loading }: { plots: Plot[]; loading: boolean }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const language = useUiStore((s) => s.language);
  const areaUnit = useUiStore((s) => s.areaUnit);
  const uiCountry = useUiStore((s) => s.country);
  // One date style for the whole table (the app's language); areas keep each plot's regional format.
  const dateLocale = intlLocale(language, uiCountry);
  const selectedPlotId = useUiStore((s) => s.selectedPlotId);
  const setSelectedPlotId = useUiStore((s) => s.setSelectedPlotId);
  const deletePlot = useDeletePlot();

  if (loading) return <PageSpinner />;
  if (plots.length === 0) {
    return (
      <div className="card flex flex-col items-center gap-3 px-6 py-10 text-center">
        <p className="m-0 max-w-[460px] text-sm text-ink-2">{t('data.emptyPlots')}</p>
        <Link to="/app" className={buttonClass('primary', 'md')}>
          {t('data.goToMap')}
        </Link>
      </div>
    );
  }

  const openOnMap = (plotId: string) => {
    setSelectedPlotId(plotId);
    navigate('/app');
  };
  const remove = (plot: Plot) => {
    if (!window.confirm(t('data.deletePlotConfirm', { name: plot.name }))) return;
    deletePlot.mutate(plot.plot_id, {
      onSuccess: () => {
        if (selectedPlotId === plot.plot_id) setSelectedPlotId(null);
      },
    });
  };

  return (
    <div className="card overflow-x-auto">
      <table className="w-full min-w-[760px] border-collapse text-sm">
        <thead>
          <tr className="text-left text-[12px] text-muted">
            {['colName', 'colArea', 'colSource', 'colAdded', 'colActions'].map((k) => (
              <th key={k} scope="col" className={`border-b border-line px-4 py-3 font-medium ${k === 'colActions' ? 'text-right' : ''}`}>
                {t(`data.${k}`)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {plots.map((p) => {
            const locale = intlLocale(language, p.country);
            const area = formatArea(p.area_hectares, p.country, locale, areaUnit);
            return (
              <tr key={p.plot_id} className="border-b border-[#EEF2EF] last:border-0">
                <td className="px-4 py-3">
                  <span className="font-semibold text-ink">{p.name}</span>
                  <span className="block font-mono text-[11px] text-muted">
                    {p.plot_id}
                    {p.region ? ` · ${p.region}` : ''}
                  </span>
                </td>
                <td className="px-4 py-3 font-mono">{area.primary}</td>
                <td className="px-4 py-3 text-ink-2">
                  <span className="flex flex-wrap items-center gap-1.5">
                    {t(plotSourceKey(p.source))}
                    {isApproximate(p) && <Pill tone="blue">{t('data.approximate')}</Pill>}
                  </span>
                </td>
                <td className="px-4 py-3 text-ink-2">{formatDate(p.created_at, dateLocale)}</td>
                <td className="px-4 py-3">
                  <div className="flex justify-end gap-1.5">
                    <Button size="sm" variant="secondary" onClick={() => openOnMap(p.plot_id)}>
                      <MapPinned size={14} aria-hidden="true" />
                      {t('data.openOnMap')}
                    </Button>
                    <Link to={`/app/plots/${p.plot_id}/results`} onClick={() => setSelectedPlotId(p.plot_id)} className={buttonClass('secondary', 'sm')}>
                      <ChartColumn size={14} aria-hidden="true" />
                      {t('data.results')}
                    </Link>
                    <Button size="sm" variant="ghost" aria-label={t('data.deleteNamed', { name: p.name })} title={t('data.delete')} onClick={() => remove(p)}>
                      <Trash2 size={14} aria-hidden="true" />
                    </Button>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
