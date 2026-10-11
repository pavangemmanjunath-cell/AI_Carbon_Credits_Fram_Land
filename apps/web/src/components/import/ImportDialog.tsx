import { useEffect, useMemo, useRef, useState, type DragEvent } from 'react';
import {
  Boxes,
  CircleCheckBig,
  CloudUpload,
  File as FileIcon,
  FileCode,
  FileSpreadsheet,
  ShieldCheck,
  X,
} from 'lucide-react';
import { Trans, useTranslation } from 'react-i18next';
import { Button } from '@/components/ui/Button';
import { Dialog } from '@/components/ui/Dialog';
import { InfoButton } from '@/components/ui/InfoButton';
import { Switch } from '@/components/ui/Switch';
import { regionIdFor, type AreaUnit } from '@/config/regions';
import { DEFAULT_FORM } from '@/features/workspace/logic/workspaceModel';
import { errorMessage } from '@/lib/errors';
import { formatArea, formatInteger, formatNumber, intlLocale } from '@/lib/format';
import {
  formatBytes,
  importOutcomes,
  IMPORT_ACCEPT,
  treeCountToUse,
  type ImportFileType,
  type TreeFormDefaults,
} from '@/lib/imports';
import { usePlots, useSpecies } from '@/services/queries';
import { useUiStore } from '@/store/uiStore';
import type { Plot } from '@/types/api';
import {
  useImportQueue,
  type ActionState,
  type ImportQueue,
  type QueueItem,
} from './useImportQueue';

function TypeIcon({ type }: { type: ImportFileType }) {
  const Icon =
    type === 'las' || type === 'laz' || type === 'e57'
      ? Boxes
      : type === 'csv'
        ? FileSpreadsheet
        : type === 'unknown'
          ? FileIcon
          : FileCode;
  return (
    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[8px] bg-mint text-forest-deep">
      <Icon size={18} aria-hidden="true" />
    </span>
  );
}

/** Trimble-style "Import data": drop zone, file list, two switches, Cancel / Import. */
export function ImportDialog({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation();
  const language = useUiStore((s) => s.language);
  const country = useUiStore((s) => s.country);
  const areaUnit = useUiStore((s) => s.areaUnit);
  const selectedPlotId = useUiStore((s) => s.selectedPlotId);
  const setSelectedPlotId = useUiStore((s) => s.setSelectedPlotId);
  const activeTreeForm = useUiStore((s) => s.activeTreeForm);
  const plots = usePlots().data?.items;
  const plotList = useMemo(() => plots ?? [], [plots]);
  const selectedPlot = plotList.find((p) => p.plot_id === selectedPlotId) ?? null;
  const species = useSpecies(regionIdFor(selectedPlot?.country ?? country)).data;
  const [useBoundaryAsLand, setUseBoundaryAsLand] = useState(true);
  const [runDetection, setRunDetection] = useState(true);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const locale = intlLocale(language, selectedPlot?.country ?? country);

  const treeDefaults: TreeFormDefaults | null = useMemo(() => {
    if (activeTreeForm) return activeTreeForm;
    const fallbackSpecies = species?.[0]?.id;
    if (!fallbackSpecies) return null;
    return {
      species_id: fallbackSpecies,
      plantation_year: DEFAULT_FORM.plantation_year,
      survival_rate: DEFAULT_FORM.survival_rate,
    };
  }, [activeTreeForm, species]);

  const queue = useImportQueue({
    // Link by the stored selection even before the plot list has loaded.
    plotId: selectedPlotId ?? null,
    plots: plotList,
    runDetection,
    useBoundaryAsLand,
    treeDefaults,
    plotNamePrefix: t('map.newPlotPrefix'),
    onPlotCreated: (plot) => setSelectedPlotId(plot.plot_id),
  });
  const { cancel } = queue;
  // Closing the dialog mid-upload cancels the rest of the queue.
  useEffect(() => () => cancel(), [cancel]);

  const addFiles = (files: FileList | File[] | null) => {
    if (!files || files.length === 0) return;
    queue.addFiles(Array.from(files));
  };
  const onDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragOver(false);
    addFiles(event.dataTransfer?.files ?? null);
  };
  const close = () => {
    queue.cancel();
    onClose();
  };

  const running = queue.phase === 'running';
  const finished = queue.phase === 'finished';
  const footer = (
    <>
      <Button variant="secondary" onClick={close}>
        {finished ? t('app.close') : t('app.cancel')}
      </Button>
      {finished ? (
        <Button onClick={onClose}>{t('import.done')}</Button>
      ) : (
        <Button onClick={() => void queue.start()} disabled={!queue.hasReady || running}>
          <CloudUpload size={16} aria-hidden="true" />
          {running ? t('import.importing') : t('import.import')}
        </Button>
      )}
    </>
  );

  return (
    <Dialog open title={t('import.title')} onClose={close} size="lg" footer={footer}>
      <div className="flex flex-col gap-4">
        <div
          onDragOver={(event) => {
            event.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={onDrop}
          data-testid="import-drop-zone"
          className={`flex flex-col items-center justify-center gap-2 rounded-[12px] border-2 border-dashed px-6 py-8 text-center transition-colors ${
            dragOver ? 'border-forest bg-mint' : 'border-line bg-ground'
          }`}
        >
          <CloudUpload size={34} className="text-forest" aria-hidden="true" />
          <p className="m-0 max-w-[440px] text-[15px] font-medium text-ink">
            <Trans
              i18nKey="import.dropText"
              components={{
                browse: (
                  <button
                    type="button"
                    className="font-semibold text-forest underline underline-offset-2"
                    onClick={() => inputRef.current?.click()}
                  />
                ),
              }}
            />
          </p>
          <p className="m-0 text-[12px] text-muted">{t('import.e57Note')}</p>
          <label className="sr-only">
            {t('import.chooseFiles')}
            <input
              ref={inputRef}
              type="file"
              multiple
              accept={IMPORT_ACCEPT}
              onChange={(event) => {
                addFiles(event.target.files);
                event.target.value = '';
              }}
            />
          </label>
        </div>

        {queue.queue.length > 0 && (
          <ul aria-label={t('import.fileList')} className="m-0 flex list-none flex-col gap-2 p-0">
            {queue.queue.map((item) => (
              <FileRow
                key={item.id}
                item={item}
                queue={queue}
                plots={plotList}
                locale={locale}
                country={selectedPlot?.country ?? country}
                areaUnit={areaUnit}
                canUseTrees={Boolean(treeDefaults)}
              />
            ))}
          </ul>
        )}

        <div className="flex flex-col gap-3 rounded-[12px] border border-line p-3.5">
          <Switch
            checked={useBoundaryAsLand}
            onChange={setUseBoundaryAsLand}
            label={t('import.useBoundary')}
            hint={t('import.useBoundaryHint')}
            disabled={running}
          />
          <Switch
            checked={runDetection}
            onChange={setRunDetection}
            label={t('import.runDetection')}
            disabled={running}
            extra={<InfoButton label={t('panel.whatIsThis')} text={t('import.runDetectionInfo')} />}
          />
        </div>

        <div className="flex flex-col gap-1 text-[12px] text-ink-2">
          <p className="m-0 flex items-center gap-2">
            <ShieldCheck size={15} className="shrink-0 text-forest" aria-hidden="true" />
            {t('import.privacy')}
          </p>
          <p className="m-0 pl-[23px] text-muted">
            {selectedPlot
              ? t('import.linkedTo', { plot: selectedPlot.name })
              : t('import.notLinked')}
          </p>
        </div>
      </div>
    </Dialog>
  );
}

interface RowProps {
  item: QueueItem;
  queue: ImportQueue;
  plots: Plot[];
  locale: string;
  country: string;
  areaUnit: AreaUnit | 'auto';
  canUseTrees: boolean;
}

function actionLabel(
  state: ActionState | undefined,
  labels: { idle: string; pending: string; done: (name: string) => string },
): { text: string; disabled: boolean; done: boolean } {
  if (!state || state.status === 'idle' || state.status === 'error')
    return { text: labels.idle, disabled: false, done: false };
  if (state.status === 'pending') return { text: labels.pending, disabled: true, done: false };
  return { text: labels.done(state.plotName), disabled: true, done: true };
}

function FileRow({ item, queue, plots, locale, country, areaUnit, canUseTrees }: RowProps) {
  const { t } = useTranslation();
  const record = item.record;
  const pct = Math.round(item.progress * 100);
  const target: Plot | null = queue.treeTarget;
  const land = queue.landActions[item.id];
  const trees = queue.treeActions[item.id];

  return (
    <li className="flex items-start gap-3 rounded-[10px] border border-line bg-surface px-3 py-2.5">
      <TypeIcon type={item.type} />
      <div className="flex min-w-0 flex-1 flex-col gap-1.5">
        <div className="flex flex-wrap items-baseline gap-x-2">
          <span className="min-w-0 truncate text-sm font-medium text-ink" title={item.file.name}>
            {item.file.name}
          </span>
          <span className="text-[12px] text-muted">
            {formatBytes(item.file.size, locale)} · {t(`import.type_${item.type}`)}
          </span>
        </div>

        {item.status === 'unsupported' && (
          <span className="text-[12px] text-amber-text">{t('import.unsupported')}</span>
        )}
        {item.status === 'cancelled' && (
          <span className="text-[12px] text-muted">{t('import.status_cancelled')}</span>
        )}
        {item.status === 'uploading' && (
          <div className="flex items-center gap-2" aria-live="polite">
            <span className="block h-1.5 flex-1 overflow-hidden rounded-full bg-[#E3E9E4]">
              <span
                className="block h-full bg-forest transition-[width]"
                style={{ width: `${pct}%` }}
              />
            </span>
            <span className="w-24 shrink-0 text-right font-mono text-[11px] text-ink-2">
              {pct >= 100 ? t('import.analysing') : t('import.uploading', { pct })}
            </span>
          </div>
        )}
        {item.status === 'error' && (
          <span role="alert" className="text-[12px] text-amber-text">
            {t('import.failed')}: {errorMessage(item.error, t)}
          </span>
        )}

        {item.status === 'done' &&
          record &&
          importOutcomes(record).map((outcome) => {
            if (outcome.kind === 'failed') {
              return (
                <span key="failed" role="alert" className="text-[12px] text-amber-text">
                  {t('import.failed')}
                  {outcome.reason ? `: ${outcome.reason}` : ''}
                </span>
              );
            }
            if (outcome.kind === 'nothing') {
              return (
                <span key="nothing" className="text-[12px] text-ink-2">
                  {t('import.nothingFound')}
                </span>
              );
            }
            if (outcome.kind === 'boundary') {
              const area = formatArea(outcome.areaHectares, country, locale, areaUnit).primary;
              const action = actionLabel(land, {
                idle: t('import.useAsLand'),
                pending: t('import.adding'),
                done: (name) => t('import.addedAsLand', { name }),
              });
              return (
                <div key="boundary" className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-[13px] text-ink">
                    {t('import.boundaryFound', { area })}
                  </span>
                  <Button
                    size="sm"
                    variant={action.done ? 'ghost' : 'secondary'}
                    disabled={action.disabled}
                    onClick={() => void queue.applyAsLand(item.id, record)}
                  >
                    {action.done && (
                      <CircleCheckBig size={14} className="text-forest" aria-hidden="true" />
                    )}
                    {action.text}
                  </Button>
                  {land?.status === 'error' && (
                    <span role="alert" className="w-full text-[12px] text-amber-text">
                      {errorMessage(land.error, t)}
                    </span>
                  )}
                </div>
              );
            }
            const count = treeCountToUse(record, target?.plot_id) ?? outcome.count;
            const linked = record.plot_id
              ? (plots.find((p) => p.plot_id === record.plot_id) ?? null)
              : null;
            const n = formatInteger(outcome.count, locale);
            const detected =
              outcome.meanHeightM != null
                ? t('import.treesDetectedHeight', {
                    count: outcome.count,
                    n,
                    height: formatNumber(outcome.meanHeightM, locale, { maximumFractionDigits: 1 }),
                  })
                : t('import.treesDetected', { count: outcome.count, n });
            const action = actionLabel(trees, {
              idle: target
                ? t('import.useTrees', {
                    count,
                    n: formatInteger(count, locale),
                    plot: target.name,
                  })
                : '',
              pending: t('import.saving'),
              done: (name) => t('import.treesUsed', { plot: name }),
            });
            return (
              <div key="trees" className="flex flex-col gap-1.5">
                <span className="text-[13px] text-ink">
                  {detected}
                  {outcome.countInPlot != null &&
                    outcome.countInPlot !== outcome.count &&
                    linked && (
                      <span className="text-ink-2">
                        {' '}
                        ·{' '}
                        {t('import.insidePlot', {
                          n: formatInteger(outcome.countInPlot, locale),
                          plot: linked.name,
                        })}
                      </span>
                    )}
                </span>
                {target && canUseTrees ? (
                  <span className="flex flex-wrap items-center gap-2">
                    <Button
                      size="sm"
                      variant={action.done ? 'ghost' : 'secondary'}
                      disabled={action.disabled}
                      onClick={() => void queue.applyTrees(item.id, record, target)}
                    >
                      {action.done && (
                        <CircleCheckBig size={14} className="text-forest" aria-hidden="true" />
                      )}
                      {action.text}
                    </Button>
                    {trees?.status === 'error' && (
                      <span role="alert" className="text-[12px] text-amber-text">
                        {errorMessage(trees.error, t)}
                      </span>
                    )}
                  </span>
                ) : (
                  <span className="text-[12px] text-muted">{t('import.needLandForTrees')}</span>
                )}
              </div>
            );
          })}

        {item.status === 'done' &&
          record &&
          record.warnings.length > 0 &&
          record.status !== 'failed' && (
            <ul className="m-0 list-disc pl-4 text-[11px] text-muted">
              {record.warnings.slice(0, 3).map((w) => (
                <li key={w}>{w}</li>
              ))}
            </ul>
          )}
      </div>
      <button
        type="button"
        aria-label={t('import.remove', { name: item.file.name })}
        disabled={item.status === 'uploading'}
        onClick={() => queue.remove(item.id)}
        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-ink-2 hover:bg-ground disabled:opacity-40"
      >
        <X size={16} aria-hidden="true" />
      </button>
    </li>
  );
}
