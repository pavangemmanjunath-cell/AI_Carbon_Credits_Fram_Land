import type { Analysis, CarbonEstimate, ExplainBody, Plot, TreeInventory } from '@/types/api';

/** Mono-spaced provenance tree shown on the results page and in exports. */
export function evidenceChainLines(plot: Plot, inventory: TreeInventory | null, analysis: Analysis | undefined, estimate: CarbonEstimate): string[] {
  const e = estimate.estimate;
  const land = analysis?.landcover;
  const veg = analysis?.vegetation;
  const climate = analysis?.climate;
  const prov = estimate.provenance as unknown as { climate_zone?: { zone?: string; source?: string }; parameter_set?: { id?: string; version?: string; verification_status?: string } };
  const topClasses = (land?.classes ?? [])
    .slice(0, 2)
    .map((c) => `${c.name.toLowerCase()} ${Math.round(c.share * 100)}%`)
    .join(' · ');
  const lines = [
    `Carbon estimate · ${e.central} ${e.unit} (${e.low} – ${e.high})`,
    `├── Plot          ${plot.area_hectares} ha · ${plot.plot_id} · ${plot.source}`,
  ];
  if (inventory) {
    lines.push(
      `├── Trees         ${inventory.tree_count} · ${inventory.species.scientific_name} · planted ${inventory.plantation_year} · ${inventory.measurement_source}`,
    );
  }
  if (land) lines.push(`├── Land cover    ${land.dataset} ${land.version} · ${topClasses}`);
  if (veg?.indices.ndvi.value != null) {
    lines.push(`├── Satellite     Sentinel-2 L2A · ${veg.indices.ndvi.scene_id ?? 'scene'} · ${veg.indices.ndvi.date ?? ''}`);
    const ndmi = veg.indices.ndmi?.value != null ? ` · NDMI ${veg.indices.ndmi.value}` : '';
    const trend = veg.trend?.change_pct != null ? ` · trend ${veg.trend.change_pct > 0 ? '+' : ''}${veg.trend.change_pct}%` : '';
    lines.push(`├── Indices       NDVI ${veg.indices.ndvi.value}${ndmi}${trend}`);
  }
  if (climate) lines.push(`├── Climate zone  ${climate.zone_label ?? climate.zone} · ${climate.zone_source ?? prov.climate_zone?.source ?? 'derived'}`);
  lines.push(`├── Model         ${estimate.model.id} v${estimate.model.version} · tier ${estimate.model.tier ?? '1'} · ${estimate.methodology.name}`);
  const verified = estimate.parameters_used.filter((p) => p.verification_status === 'verified').length;
  const pending = estimate.parameters_used.filter((p) => p.verification_status === 'pending').length;
  const assumed = estimate.parameters_used.filter((p) => p.verification_status === 'assumption').length;
  lines.push(`├── Parameters    ${prov.parameter_set?.id ?? 'parameter set'} v${prov.parameter_set?.version ?? ''} · ${verified} verified · ${pending} pending · ${assumed} assumption`);
  lines.push(`└── Generated     ${estimate.generated_at} · api v${estimate.provenance.api_version} · mode ${estimate.provenance.mode} · certified: false`);
  return lines;
}

/** Only derived indicators — never coordinates, names or geometry — reach /explain. */
export function explainBody(language: string, inventory: TreeInventory | null, analysis: Analysis | undefined, estimate: CarbonEstimate, plot: Plot): ExplainBody {
  return {
    language,
    indicators: {
      area_hectares: plot.area_hectares,
      tree_count: inventory?.tree_count,
      species: inventory?.species.common_name,
      ndvi: analysis?.vegetation?.indices.ndvi.value ?? undefined,
      ndvi_trend_pct: analysis?.vegetation?.trend?.change_pct ?? undefined,
      estimate_central: estimate.estimate.central,
      estimate_low: estimate.estimate.low,
      estimate_high: estimate.estimate.high,
      confidence: estimate.confidence,
      missing_evidence: estimate.readiness.missing_evidence.map((m) => m.id),
    },
  };
}

export interface ParameterCounts {
  verified: number;
  pending: number;
  assumption: number;
}

export function parameterCounts(estimate: CarbonEstimate): ParameterCounts {
  return estimate.parameters_used.reduce<ParameterCounts>(
    (acc, p) => {
      if (p.verification_status === 'verified') acc.verified += 1;
      else if (p.verification_status === 'pending') acc.pending += 1;
      else acc.assumption += 1;
      return acc;
    },
    { verified: 0, pending: 0, assumption: 0 },
  );
}

/** Export bundle: everything on the page, JSON only. */
/** A plot without its private fields (exact boundary, exact centroid, perimeter, bbox). */
export function publicPlot(plot: Plot) {
  return { ...plot, geometry: undefined, centroid: undefined, perimeter_m: undefined, bbox: undefined };
}

export function resultsExport(plot: Plot, inventory: TreeInventory | null, analysis: Analysis | undefined, estimate: CarbonEstimate, extras: Record<string, unknown>) {
  return {
    exported_at: new Date().toISOString(),
    disclaimer: estimate.disclaimer,
    plot: publicPlot(plot),
    inventory,
    analysis,
    estimate,
    ...extras,
  };
}
