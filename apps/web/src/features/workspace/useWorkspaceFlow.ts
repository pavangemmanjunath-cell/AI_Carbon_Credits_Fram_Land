import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { hasSatelliteOverride, mapEnv } from '@/config/mapEnv';
import { regionIdFor } from '@/config/regions';
import { useDebouncedValue } from '@/hooks/useDebouncedValue';
import { imageryCountry, resolveImagery } from '@/lib/imagery';
import { nextPlotName, type NewPlotRequest } from '@/lib/landInput';
import {
  queryKeys,
  useAnalysis,
  useCarbonEstimate,
  useCreatePlot,
  useCreateTrees,
  useCube,
  useDeletePlot,
  useDetection,
  useImageryProviders,
  useImportRecord,
  useImports,
  usePlots,
  useSpecies,
  useTrees,
} from '@/services/queries';
import { useUiStore } from '@/store/uiStore';
import type { Plot } from '@/types/api';
import { DEFAULT_FORM, formEquals, formForPlot, formFromInventory, isExternalInventory, isFormValid, toInventoryBody, type TreeForm } from './logic/workspaceModel';
import { latestInventory as pickLatestInventory } from '@/lib/insights';

/**
 * Orchestrates the main screen: plots → selection → analysis → trees → estimate.
 * Tree edits are debounced and saved as a new inventory version; the estimate
 * follows automatically. Components only render what this hook returns.
 */
export function useWorkspaceFlow() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const selectedPlotId = useUiStore((s) => s.selectedPlotId);
  const setSelectedPlotId = useUiStore((s) => s.setSelectedPlotId);
  const country = useUiStore((s) => s.country);
  const setCountry = useUiStore((s) => s.setCountry);
  const layers = useUiStore((s) => s.layers);
  const imageryChoice = useUiStore((s) => s.imageryChoice);
  const mapImportId = useUiStore((s) => s.mapImportId);
  const setMapImportId = useUiStore((s) => s.setMapImportId);
  const setActiveTreeForm = useUiStore((s) => s.setActiveTreeForm);

  const plotsQuery = usePlots();
  const plots = useMemo(() => plotsQuery.data?.items ?? [], [plotsQuery.data]);

  // Pick a sensible plot on first load so the screen is never empty.
  useEffect(() => {
    if (plots.length === 0) return;
    const exists = plots.some((p) => p.plot_id === selectedPlotId);
    if (!exists) {
      const preferred = plots.find((p) => regionIdFor(p.country) === regionIdFor(country)) ?? plots[0];
      setSelectedPlotId(preferred.plot_id);
    }
  }, [plots, selectedPlotId, setSelectedPlotId, country]);

  const selectedPlot: Plot | null = plots.find((p) => p.plot_id === selectedPlotId) ?? null;
  useEffect(() => {
    if (selectedPlot && regionIdFor(selectedPlot.country) !== regionIdFor(country)) setCountry(regionIdFor(selectedPlot.country));
  }, [selectedPlot, country, setCountry]);

  const analysisQuery = useAnalysis(selectedPlot?.plot_id);
  const treesQuery = useTrees(selectedPlot?.plot_id);
  const latestInventory = pickLatestInventory(treesQuery.data?.items);
  const speciesQuery = useSpecies(regionIdFor(selectedPlot?.country ?? country));
  const speciesList = useMemo(() => speciesQuery.data ?? [], [speciesQuery.data]);
  const cubeQuery = useCube(selectedPlot?.plot_id, 'ndvi', true);

  // -- tree form ----------------------------------------------------------------
  const [form, setForm] = useState<TreeForm>(DEFAULT_FORM);
  const formPlotRef = useRef<string | null>(null);
  const seenInventoryRef = useRef<string | null>(null);
  const ownInventoryIds = useRef(new Set<string>());
  const pendingPrefill = useRef<{ plotId: string; treeCount: number } | null>(null);
  useEffect(() => {
    if (!selectedPlot || treesQuery.isLoading) return;
    const latestId = latestInventory?.inventory_id ?? null;
    if (formPlotRef.current !== selectedPlot.plot_id) {
      formPlotRef.current = selectedPlot.plot_id;
      seenInventoryRef.current = latestId;
      const prefill = pendingPrefill.current?.plotId === selectedPlot.plot_id ? pendingPrefill.current.treeCount : null;
      if (prefill) pendingPrefill.current = null;
      setForm(formForPlot(latestInventory, speciesList[0]?.id ?? DEFAULT_FORM.species_id, prefill));
      return;
    }
    if (latestInventory && isExternalInventory(latestId, seenInventoryRef.current, ownInventoryIds.current)) {
      seenInventoryRef.current = latestId;
      setForm(formFromInventory(latestInventory, latestInventory.species.id));
    }
  }, [selectedPlot, latestInventory, speciesList, treesQuery.isLoading]);

  // The Import dialog reuses species, year and survival of the form being edited.
  useEffect(() => {
    if (!selectedPlot || formPlotRef.current !== selectedPlot.plot_id) return;
    setActiveTreeForm({ plotId: selectedPlot.plot_id, species_id: form.species_id, plantation_year: form.plantation_year, survival_rate: form.survival_rate });
  }, [selectedPlot, form.species_id, form.plantation_year, form.survival_rate, setActiveTreeForm]);

  const createTrees = useCreateTrees(selectedPlot?.plot_id);
  const debouncedForm = useDebouncedValue(form, 600);
  useEffect(() => {
    if (!selectedPlot || treesQuery.isLoading || formPlotRef.current !== selectedPlot.plot_id) return;
    if (!isFormValid(debouncedForm)) return;
    const current = formFromInventory(latestInventory, debouncedForm.species_id);
    if (latestInventory && formEquals(current, debouncedForm)) return;
    createTrees.mutate(toInventoryBody(debouncedForm), {
      onSuccess: (inventory) => {
        ownInventoryIds.current.add(inventory.inventory_id);
        seenInventoryRef.current = inventory.inventory_id;
        void queryClient.invalidateQueries({ queryKey: queryKeys.estimate(selectedPlot.plot_id) });
      },
    });
    // Saves only when the debounced form changes; the inventory it compares with is read at that moment.
  }, [debouncedForm, selectedPlot?.plot_id, treesQuery.isLoading]);

  const estimateQuery = useCarbonEstimate(selectedPlot?.plot_id, latestInventory?.inventory_id ?? null, Boolean(latestInventory));

  // -- map data: AI tree cover, imported trees, satellite imagery ----------------------
  const detectionQuery = useDetection(selectedPlot?.plot_id, layers.treeCover);
  const importsQuery = useImports(selectedPlot?.plot_id, layers.importedTrees && Boolean(selectedPlot) && !mapImportId);
  const latestTreeImport = importsQuery.data?.items.find((i) => i.status !== 'failed' && (i.trees?.count ?? 0) > 0) ?? null;
  const importIdOnMap = layers.importedTrees ? (mapImportId ?? latestTreeImport?.import_id ?? null) : null;
  const importRecordQuery = useImportRecord(importIdOnMap);
  // An import opened from the Data page belongs to its own plot: drop it when another plot is chosen.
  const importRecord = importRecordQuery.data;
  useEffect(() => {
    if (mapImportId && importRecord?.import_id === mapImportId && importRecord.plot_id && selectedPlot && importRecord.plot_id !== selectedPlot.plot_id) {
      setMapImportId(null);
    }
  }, [mapImportId, importRecord, selectedPlot, setMapImportId]);

  const imageryKey = imageryCountry(selectedPlot?.country, country);
  const imageryQuery = useImageryProviders(imageryKey, !hasSatelliteOverride);
  const preferredImagery = imageryChoice[imageryKey ?? 'default'];
  // Memoised: a new provider object would make the map re-sync its imagery on every render.
  const imageryProvider = useMemo(
    () =>
      resolveImagery({
        envUrl: mapEnv.satelliteTilesUrl,
        envAttribution: mapEnv.satelliteAttribution,
        response: imageryQuery.data,
        preferredId: preferredImagery,
      }),
    [imageryQuery.data, preferredImagery],
  );

  // -- plot commands -------------------------------------------------------------
  const createPlot = useCreatePlot();
  const deletePlot = useDeletePlot();
  const onCreatePlot = useCallback(
    (request: NewPlotRequest) => {
      const name = request.name ?? nextPlotName(plots, t('map.newPlotPrefix'));
      // `country` is left to the server, which derives it from the polygon.
      createPlot.mutate(
        { name, geometry: request.geometry, source: request.source, boundary_quality: request.boundary_quality },
        {
          onSuccess: (plot) => {
            if (request.treeCount && request.treeCount > 0) pendingPrefill.current = { plotId: plot.plot_id, treeCount: request.treeCount };
            setSelectedPlotId(plot.plot_id);
          },
        },
      );
    },
    [createPlot, plots, t, setSelectedPlotId],
  );
  const onDeletePlot = useCallback(
    (plotId: string) => {
      deletePlot.mutate(plotId, {
        onSuccess: () => {
          if (selectedPlotId === plotId) setSelectedPlotId(null);
        },
      });
    },
    [deletePlot, selectedPlotId, setSelectedPlotId],
  );

  return {
    plots,
    plotsLoading: plotsQuery.isLoading,
    selectedPlot,
    selectPlot: setSelectedPlotId,
    country,
    analysis: analysisQuery.data,
    analysisLoading: analysisQuery.isLoading,
    cube: cubeQuery.data,
    species: speciesList,
    latestInventory,
    form,
    setForm,
    savingTrees: createTrees.isPending,
    estimate: estimateQuery.data,
    estimateLoading: estimateQuery.isLoading || estimateQuery.isFetching,
    estimateError: estimateQuery.error,
    detection: { data: detectionQuery.data, loading: detectionQuery.isFetching, error: detectionQuery.error },
    importedTrees: { record: importRecord ?? null, loading: importsQuery.isFetching || importRecordQuery.isFetching, error: importsQuery.error ?? importRecordQuery.error, fitOnLoad: Boolean(mapImportId) },
    imagery: { provider: imageryProvider, loading: imageryQuery.isLoading },
    onCreatePlot,
    onDeletePlot,
    creatingPlot: createPlot.isPending,
    createPlotError: createPlot.error,
  };
}

export type WorkspaceFlow = ReturnType<typeof useWorkspaceFlow>;
