import { CloudUpload, Database } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useSearchParams } from 'react-router';
import { Button } from '@/components/ui/Button';
import { useImports, usePlots } from '@/services/queries';
import { useUiStore } from '@/store/uiStore';
import { FilesTable } from './FilesTable';
import { PlotsTable } from './PlotsTable';
import { tabFromParam, type DataTab } from './logic/dataModel';

/** Trimble-style Data page: "Land plots" and "Imported files", with the Import button. */
export default function DataPage() {
  const { t } = useTranslation();
  const [params, setParams] = useSearchParams();
  const tab = tabFromParam(params.get('tab'));
  const setImportOpen = useUiStore((s) => s.setImportOpen);
  const plotsQuery = usePlots();
  const importsQuery = useImports();
  const plots = plotsQuery.data?.items ?? [];

  const select = (next: DataTab) => {
    const p = new URLSearchParams(params);
    if (next === 'files') p.set('tab', 'files');
    else p.delete('tab');
    setParams(p, { replace: true });
  };
  const tabs: { id: DataTab; label: string; count: number | null }[] = [
    { id: 'plots', label: t('data.tabPlots'), count: plotsQuery.data ? plots.length : null },
    {
      id: 'files',
      label: t('data.tabFiles'),
      count: importsQuery.data ? importsQuery.data.items.length : null,
    },
  ];

  return (
    <div className="mx-auto flex max-w-[1240px] flex-col gap-4 p-4 lg:p-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="flex flex-col gap-1">
          <h1 className="m-0 flex items-center gap-2.5 text-[24px]">
            <Database size={22} className="text-forest" aria-hidden="true" />
            {t('data.title')}
          </h1>
          <p className="m-0 text-sm text-ink-2">{t('data.subtitle')}</p>
        </div>
        <Button onClick={() => setImportOpen(true)}>
          <CloudUpload size={16} aria-hidden="true" />
          {t('nav.import')}
        </Button>
      </div>

      <div role="tablist" aria-label={t('data.title')} className="flex gap-1 border-b border-line">
        {tabs.map((item) => (
          <button
            key={item.id}
            id={`data-tab-${item.id}`}
            type="button"
            role="tab"
            aria-selected={tab === item.id}
            aria-controls={`data-panel-${item.id}`}
            tabIndex={tab === item.id ? 0 : -1}
            onClick={() => select(item.id)}
            onKeyDown={(e) => {
              if (e.key === 'ArrowRight' || e.key === 'ArrowLeft')
                select(item.id === 'plots' ? 'files' : 'plots');
            }}
            className={`-mb-px flex h-11 items-center gap-2 border-b-2 px-3.5 text-sm font-semibold transition-colors ${
              tab === item.id
                ? 'border-forest text-forest-deep'
                : 'border-transparent text-ink-2 hover:text-ink'
            }`}
          >
            {item.label}
            {item.count != null && (
              <span className="rounded-full bg-ground px-2 py-0.5 font-mono text-[11px] text-muted">
                {item.count}
              </span>
            )}
          </button>
        ))}
      </div>

      <div role="tabpanel" id={`data-panel-${tab}`} aria-labelledby={`data-tab-${tab}`}>
        {tab === 'plots' ? (
          <PlotsTable plots={plots} loading={plotsQuery.isLoading} />
        ) : (
          <FilesTable
            records={importsQuery.data?.items ?? []}
            plots={plots}
            loading={importsQuery.isLoading}
            error={importsQuery.error}
          />
        )}
      </div>
    </div>
  );
}
