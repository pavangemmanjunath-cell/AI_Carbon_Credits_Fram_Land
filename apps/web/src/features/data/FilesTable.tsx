import { Boxes, CloudUpload, File as FileIcon, FileCode, FileSpreadsheet, MapPinned, Trash2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router';
import { Button } from '@/components/ui/Button';
import { PageSpinner } from '@/components/ui/PageSpinner';
import { errorMessage } from '@/lib/errors';
import { formatArea, formatDate, formatInteger, formatNumber, intlLocale } from '@/lib/format';
import { formatBytes, isPointCloud, type ImportFileType } from '@/lib/imports';
import { useDeleteImport } from '@/services/queries';
import { useUiStore } from '@/store/uiStore';
import type { ImportRecord, Plot } from '@/types/api';
import { canShowOnMap, importResultLine, importTypeOf, linkedPlot } from './logic/dataModel';

function TypeIcon({ type }: { type: ImportFileType }) {
  const Icon = isPointCloud(type) ? Boxes : type === 'csv' ? FileSpreadsheet : type === 'unknown' ? FileIcon : FileCode;
  return <Icon size={16} className="shrink-0 text-forest" aria-hidden="true" />;
}

interface Props {
  records: ImportRecord[];
  plots: Plot[];
  loading: boolean;
  error: unknown;
}

/** "Imported files" tab — like Trimble's Data list, but only the derived results are kept. */
export function FilesTable({ records, plots, loading, error }: Props) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const language = useUiStore((s) => s.language);
  const country = useUiStore((s) => s.country);
  const areaUnit = useUiStore((s) => s.areaUnit);
  const setImportOpen = useUiStore((s) => s.setImportOpen);
  const showImportOnMap = useUiStore((s) => s.showImportOnMap);
  const deleteImport = useDeleteImport();
  const locale = intlLocale(language, country);

  if (loading) return <PageSpinner />;
  if (error) {
    return (
      <p role="alert" className="card m-0 px-5 py-6 text-sm text-amber-text">
        {t('data.filesFailed')} {errorMessage(error, t)}
      </p>
    );
  }
  if (records.length === 0) {
    return (
      <div className="card flex flex-col items-center gap-3 px-6 py-10 text-center">
        <p className="m-0 max-w-[480px] text-sm text-ink-2">{t('data.emptyFiles')}</p>
        <Button onClick={() => setImportOpen(true)}>
          <CloudUpload size={16} aria-hidden="true" />
          {t('nav.import')}
        </Button>
      </div>
    );
  }

  const resultText = (record: ImportRecord, plot: Plot | null): string => {
    const line = importResultLine(record);
    const area = (ha: number) => formatArea(ha, plot?.country ?? country, locale, areaUnit).primary;
    switch (line.kind) {
      case 'boundary':
        return t('data.resultBoundary', { area: area(line.areaHectares) });
      case 'trees':
        return line.meanHeightM != null
          ? t('data.resultTreesHeight', { count: line.count, n: formatInteger(line.count, locale), height: formatNumber(line.meanHeightM, locale, { maximumFractionDigits: 1 }) })
          : t('data.resultTrees', { count: line.count, n: formatInteger(line.count, locale) });
      case 'boundary-trees':
        return `${t('data.resultBoundary', { area: area(line.areaHectares) })} · ${t('data.resultTrees', { count: line.count, n: formatInteger(line.count, locale) })}`;
      case 'failed':
        return t('data.resultFailed');
      default:
        return t('data.resultNothing');
    }
  };

  const viewOnMap = (record: ImportRecord) => {
    showImportOnMap(record.import_id, record.plot_id);
    navigate('/app');
  };
  const remove = (record: ImportRecord) => {
    if (window.confirm(t('data.deleteFileConfirm', { name: record.filename }))) deleteImport.mutate(record.import_id);
  };

  return (
    <div className="card overflow-x-auto">
      <table className="w-full min-w-[880px] border-collapse text-sm">
        <thead>
          <tr className="text-left text-[12px] text-muted">
            {['colName', 'colType', 'colSize', 'colAdded', 'colPlot', 'colResult', 'colActions'].map((k) => (
              <th key={k} scope="col" className={`border-b border-line px-4 py-3 font-medium ${k === 'colActions' ? 'text-right' : ''}`}>
                {t(`data.${k}`)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {records.map((record) => {
            const type = importTypeOf(record);
            const plot = linkedPlot(record, plots);
            const failed = record.status === 'failed';
            return (
              <tr key={record.import_id} className="border-b border-[#EEF2EF] last:border-0">
                <td className="px-4 py-3">
                  <span className="flex min-w-0 items-center gap-2">
                    <TypeIcon type={type} />
                    <span className="truncate font-semibold text-ink" title={record.filename}>
                      {record.filename}
                    </span>
                  </span>
                </td>
                <td className="px-4 py-3 text-ink-2">{t(`import.type_${type}`)}</td>
                <td className="px-4 py-3 font-mono text-ink-2">{formatBytes(record.size_bytes, locale)}</td>
                <td className="px-4 py-3 text-ink-2">{formatDate(record.created_at, locale)}</td>
                <td className="px-4 py-3 text-ink-2">{plot ? plot.name : record.plot_id ? record.plot_id : '—'}</td>
                <td className={`px-4 py-3 ${failed ? 'text-amber-text' : 'text-ink'}`}>{resultText(record, plot)}</td>
                <td className="px-4 py-3">
                  <div className="flex justify-end gap-1.5">
                    <Button size="sm" variant="secondary" disabled={!canShowOnMap(record)} onClick={() => viewOnMap(record)}>
                      <MapPinned size={14} aria-hidden="true" />
                      {t('data.viewOnMap')}
                    </Button>
                    <Button size="sm" variant="ghost" aria-label={t('data.deleteNamed', { name: record.filename })} title={t('data.delete')} onClick={() => remove(record)}>
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
