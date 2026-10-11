import { useCallback, useEffect, useReducer, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { isAbortError } from '@/lib/errors';
import {
  inventoryFromImport,
  nextReady,
  plotFromImport,
  queuePhase,
  queueReducer,
  type QueueItem,
  type TreeFormDefaults,
} from '@/lib/imports';
import { nextPlotName } from '@/lib/landInput';
import { queryKeys, useAddTrees, useCreatePlot, useUploadImport } from '@/services/queries';
import type { ImportRecord, Plot } from '@/types/api';

export type ActionState =
  | { status: 'idle' }
  | { status: 'pending' }
  | { status: 'done'; plotId: string; plotName: string }
  | { status: 'error'; error: unknown };

interface Options {
  /** Plot the uploads are linked to (`plot_id`), usually the selected plot. */
  plotId: string | null;
  plots: Plot[];
  runDetection: boolean;
  useBoundaryAsLand: boolean;
  treeDefaults: TreeFormDefaults | null;
  plotNamePrefix: string;
  onPlotCreated: (plot: Plot) => void;
}

/**
 * Orchestrates the Import dialog: one upload at a time (with progress), then
 * the follow-up actions. Pure state transitions live in `lib/imports.ts`.
 */
export function useImportQueue(options: Options) {
  const queryClient = useQueryClient();
  const [queue, dispatch] = useReducer(queueReducer, []);
  const [landActions, setLandActions] = useState<Record<string, ActionState>>({});
  const [treeActions, setTreeActions] = useState<Record<string, ActionState>>({});
  const [createdPlots, setCreatedPlots] = useState<Plot[]>([]);
  const upload = useUploadImport();
  const createPlot = useCreatePlot();
  const addTrees = useAddTrees();
  const queueRef = useRef(queue);
  const optionsRef = useRef(options);
  const abortRef = useRef<AbortController | null>(null);
  const runningRef = useRef(false);
  useEffect(() => {
    queueRef.current = queue;
    optionsRef.current = options;
  });

  const createdPlotsRef = useRef<Plot[]>([]);
  const knownPlots = useCallback(() => {
    const seen = new Map<string, Plot>();
    for (const plot of [...optionsRef.current.plots, ...createdPlotsRef.current])
      seen.set(plot.plot_id, plot);
    return [...seen.values()];
  }, []);

  const applyAsLand = useCallback(
    async (itemId: string, record: ImportRecord): Promise<Plot | null> => {
      const { plotNamePrefix, onPlotCreated } = optionsRef.current;
      const body = plotFromImport(record, nextPlotName(knownPlots(), plotNamePrefix));
      if (!body) return null;
      setLandActions((s) => ({ ...s, [itemId]: { status: 'pending' } }));
      try {
        const plot = await createPlot.mutateAsync(body);
        createdPlotsRef.current = [...createdPlotsRef.current, plot];
        setCreatedPlots(createdPlotsRef.current);
        setLandActions((s) => ({
          ...s,
          [itemId]: { status: 'done', plotId: plot.plot_id, plotName: plot.name },
        }));
        onPlotCreated(plot);
        return plot;
      } catch (error) {
        setLandActions((s) => ({ ...s, [itemId]: { status: 'error', error } }));
        return null;
      }
    },
    [createPlot, knownPlots],
  );

  const applyTrees = useCallback(
    async (itemId: string, record: ImportRecord, plot: Plot) => {
      const defaults = optionsRef.current.treeDefaults;
      if (!defaults) return;
      const body = inventoryFromImport(record, defaults, plot.plot_id);
      if (!body) return;
      setTreeActions((s) => ({ ...s, [itemId]: { status: 'pending' } }));
      try {
        await addTrees.mutateAsync({ plotId: plot.plot_id, body });
        void queryClient.invalidateQueries({ queryKey: queryKeys.estimate(plot.plot_id) });
        setTreeActions((s) => ({
          ...s,
          [itemId]: { status: 'done', plotId: plot.plot_id, plotName: plot.name },
        }));
      } catch (error) {
        setTreeActions((s) => ({ ...s, [itemId]: { status: 'error', error } }));
      }
    },
    [addTrees, queryClient],
  );

  const start = useCallback(async () => {
    if (runningRef.current) return;
    runningRef.current = true;
    const controller = new AbortController();
    abortRef.current = controller;
    const attempted = new Set<string>();
    let linkedPlotId = optionsRef.current.plotId;
    try {
      for (;;) {
        const item = queueRef.current.find((i) => i.status === 'ready' && !attempted.has(i.id));
        if (!item || controller.signal.aborted) break;
        attempted.add(item.id);
        dispatch({ type: 'start', id: item.id });
        try {
          const record = await upload.mutateAsync({
            file: item.file,
            options: {
              plotId: linkedPlotId,
              purpose: 'auto',
              runDetection: optionsRef.current.runDetection,
              signal: controller.signal,
              onProgress: (progress) => dispatch({ type: 'progress', id: item.id, progress }),
            },
          });
          dispatch({ type: 'done', id: item.id, record });
          if (
            optionsRef.current.useBoundaryAsLand &&
            record.status !== 'failed' &&
            record.boundary
          ) {
            const plot = await applyAsLand(item.id, record);
            // Later files of the same batch are counted inside the new land.
            if (plot) linkedPlotId = plot.plot_id;
          }
        } catch (error) {
          if (isAbortError(error)) {
            dispatch({ type: 'cancelPending' });
            break;
          }
          dispatch({ type: 'error', id: item.id, error });
        }
      }
    } finally {
      runningRef.current = false;
      abortRef.current = null;
    }
  }, [upload, applyAsLand]);

  const cancel = useCallback(() => {
    abortRef.current?.abort();
    dispatch({ type: 'cancelPending' });
  }, []);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    dispatch({ type: 'reset' });
    setLandActions({});
    setTreeActions({});
    createdPlotsRef.current = [];
    setCreatedPlots([]);
  }, []);

  /** Where "Use N trees" goes: the land created in this dialog, else the selected plot. */
  const treeTarget: Plot | null =
    createdPlots[createdPlots.length - 1] ??
    options.plots.find((p) => p.plot_id === options.plotId) ??
    null;

  return {
    queue,
    phase: queuePhase(queue),
    hasReady: Boolean(nextReady(queue)),
    addFiles: (files: File[]) => dispatch({ type: 'add', files }),
    remove: (id: string) => dispatch({ type: 'remove', id }),
    start,
    cancel,
    reset,
    landActions,
    treeActions,
    applyAsLand,
    applyTrees,
    treeTarget,
  };
}

export type ImportQueue = ReturnType<typeof useImportQueue>;
export type { QueueItem };
