import { FileText } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';
import { buttonClass } from '@/components/ui/buttonStyles';
import { PageSpinner } from '@/components/ui/PageSpinner';
import { formatArea, formatDate, intlLocale } from '@/lib/format';
import { usePlots } from '@/services/queries';
import { useUiStore } from '@/store/uiStore';

/** One report per plot; each opens the existing report viewer. */
export default function ReportsPage() {
  const { t } = useTranslation();
  const language = useUiStore((s) => s.language);
  const areaUnit = useUiStore((s) => s.areaUnit);
  const setSelectedPlotId = useUiStore((s) => s.setSelectedPlotId);
  const { data, isLoading } = usePlots();
  const plots = data?.items ?? [];

  return (
    <div className="mx-auto flex max-w-[1040px] flex-col gap-4 p-4 lg:p-5">
      <div className="flex flex-col gap-1">
        <h1 className="m-0 flex items-center gap-2.5 text-[24px]">
          <FileText size={22} className="text-forest" aria-hidden="true" />
          {t('reports.title')}
        </h1>
        <p className="m-0 text-sm text-ink-2">{t('reports.subtitle')}</p>
      </div>
      {isLoading ? (
        <PageSpinner />
      ) : plots.length === 0 ? (
        <div className="card flex flex-col items-center gap-3 px-6 py-10 text-center">
          <p className="m-0 text-sm text-ink-2">{t('reports.empty')}</p>
          <Link to="/app" className={buttonClass('primary', 'md')}>
            {t('data.goToMap')}
          </Link>
        </div>
      ) : (
        <ul className="m-0 flex list-none flex-col gap-2.5 p-0">
          {plots.map((p) => {
            const locale = intlLocale(language, p.country);
            return (
              <li
                key={p.plot_id}
                className="card flex flex-wrap items-center justify-between gap-3 px-4 py-3.5"
              >
                <span className="flex min-w-0 flex-col">
                  <span className="font-semibold text-ink">{p.name}</span>
                  <span className="text-[12px] text-muted">
                    {formatArea(p.area_hectares, p.country, locale, areaUnit).primary} ·{' '}
                    {t(`country.${p.country}`, { defaultValue: p.country })} ·{' '}
                    {formatDate(p.created_at, locale)}
                  </span>
                </span>
                <Link
                  to={`/app/plots/${p.plot_id}/report`}
                  onClick={() => setSelectedPlotId(p.plot_id)}
                  className={buttonClass('secondary', 'sm')}
                >
                  <FileText size={14} aria-hidden="true" />
                  {t('reports.open')}
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
