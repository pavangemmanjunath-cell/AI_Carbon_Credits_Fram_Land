import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useSearchParams } from 'react-router';
import { MapView } from '@/components/map/MapView';
import { errorMessage } from '@/lib/errors';
import { intlLocale } from '@/lib/format';
import { useUiStore } from '@/store/uiStore';
import { LockedLandCard } from './LockedLandCard';
import { PlotDetailsPanel } from './PlotDetailsPanel';
import { ResultCards } from './ResultCards';
import { useWorkspaceFlow } from './useWorkspaceFlow';

export default function WorkspacePage() {
  const { t } = useTranslation();
  const [params] = useSearchParams();
  const language = useUiStore((s) => s.language);
  const setCountry = useUiStore((s) => s.setCountry);
  const flow = useWorkspaceFlow();

  // `/app?country=IN&q=…` from the landing page
  useEffect(() => {
    const c = params.get('country');
    if (c) setCountry(c.toUpperCase());
  }, [params, setCountry]);

  const locale = intlLocale(language, flow.selectedPlot?.country ?? flow.country);

  return (
    <div className="flex flex-wrap gap-3.5 p-3.5">
      <div className="flex min-w-0 flex-[999_1_560px] flex-col gap-3.5">
        <MapView
          plots={flow.plots}
          plotsLoading={flow.plotsLoading}
          selectedPlot={flow.selectedPlot}
          cube={flow.cube}
          analysis={flow.analysis}
          analysisLoading={flow.analysisLoading}
          country={flow.country}
          locale={locale}
          initialQuery={params.get('q') ?? ''}
          imagery={flow.imagery}
          detection={flow.detection}
          importedTrees={flow.importedTrees}
          onSelectPlot={flow.selectPlot}
          onCreatePlot={flow.onCreatePlot}
          onDeletePlot={flow.onDeletePlot}
        />
        {flow.createPlotError && (
          <p
            role="alert"
            className="m-0 rounded-[10px] border border-amber-tint bg-amber-tint px-3 py-2 text-[13px] text-amber-text"
          >
            {t('map.createFailed', { reason: errorMessage(flow.createPlotError, t) })}
          </p>
        )}
        <ResultCards
          plot={flow.selectedPlot}
          inventory={flow.latestInventory}
          estimate={flow.estimate}
          analysis={flow.analysis}
          locale={locale}
          loading={flow.analysisLoading || flow.estimateLoading}
        />
        <LockedLandCard
          plot={flow.selectedPlot}
          species={flow.species}
          defaultSpeciesId={flow.form.species_id}
          locale={locale}
        />
      </div>
      <div className="w-full flex-[1_1_340px] lg:max-w-[400px]">
        <PlotDetailsPanel
          plots={flow.plots}
          plot={flow.selectedPlot}
          species={flow.species}
          form={flow.form}
          onForm={flow.setForm}
          estimate={flow.estimate}
          analysis={flow.analysis}
          saving={flow.savingTrees}
          updating={flow.estimateLoading}
          locale={locale}
          onSelectPlot={flow.selectPlot}
        />
      </div>
    </div>
  );
}
