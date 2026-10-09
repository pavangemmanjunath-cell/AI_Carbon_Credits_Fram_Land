import { useEffect, useRef } from 'react';
import { Download, Printer } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Link, useParams } from 'react-router';
import { Button } from '@/components/ui/Button';
import { PageSpinner } from '@/components/ui/PageSpinner';
import { downloadJson } from '@/lib/download';
import { useCarbonEstimate, usePlot, useReportDocument, useTrees } from '@/services/queries';
import { useUiStore } from '@/store/uiStore';
import { latestInventory } from '@/lib/insights';
import { publicPlot } from '@/features/results/logic/resultsLogic';

export default function ReportPage() {
  const { t } = useTranslation();
  const { id = '' } = useParams();
  const language = useUiStore((s) => s.language);
  const setSelectedPlotId = useUiStore((s) => s.setSelectedPlotId);
  const plot = usePlot(id).data;
  const inventory = latestInventory(useTrees(id).data?.items);
  const estimate = useCarbonEstimate(id, inventory?.inventory_id ?? null, Boolean(inventory)).data;
  const report = useReportDocument(estimate ? id : null, language, estimate?.estimate_id);
  const frame = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    if (id) setSelectedPlotId(id);
  }, [id, setSelectedPlotId]);

  const print = () => {
    const win = frame.current?.contentWindow;
    if (win) {
      win.focus();
      win.print();
    } else {
      window.print();
    }
  };

  return (
    <div className="flex flex-col gap-4 p-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="flex flex-col gap-1">
          <nav aria-label="Breadcrumb" className="flex items-center gap-2 text-[13px] text-muted">
            <Link to="/app" className="text-ink-2 no-underline hover:text-forest">{t('results.breadcrumbWorkspace')}</Link>
            <span aria-hidden="true">›</span>
            {plot && (
              <>
                <Link to={`/app/plots/${plot.plot_id}/results`} className="text-ink-2 no-underline hover:text-forest">{plot.name}</Link>
                <span aria-hidden="true">›</span>
              </>
            )}
            <span className="font-semibold text-ink">{t('report.title')}</span>
          </nav>
          <h1 className="m-0 text-[24px]">{t('report.title')}{plot ? ` · ${plot.name}` : ''}</h1>
          <p className="m-0 text-sm text-ink-2">{t('report.subtitle')}</p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={print} disabled={!report.data}>
            <Printer size={16} aria-hidden="true" /> {t('report.print')}
          </Button>
          <Button variant="secondary" onClick={() => estimate && downloadJson({ plot: plot ? publicPlot(plot) : null, inventory, estimate, report: report.data?.handle }, `${id}-report.json`)} disabled={!estimate}>
            <Download size={16} aria-hidden="true" /> {t('report.downloadJson')}
          </Button>
        </div>
      </div>
      {report.isLoading && <PageSpinner label={t('report.generating')} />}
      {report.isError && <p role="alert" className="card m-0 p-4 text-sm text-amber-text">{t('report.failed')}</p>}
      {!estimate && !report.isLoading && <p className="card m-0 p-4 text-sm text-ink-2">{t('results.noEstimate')}</p>}
      {report.data && (
        <iframe
          ref={frame}
          title={t('report.frameTitle')}
          srcDoc={report.data.html}
          sandbox="allow-same-origin allow-modals"
          className="h-[calc(100vh-220px)] min-h-[640px] w-full rounded-[14px] border border-line bg-white"
        />
      )}
    </div>
  );
}
