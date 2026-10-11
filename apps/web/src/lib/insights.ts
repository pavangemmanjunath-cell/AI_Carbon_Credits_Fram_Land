/**
 * Plain summaries of the analysis for the map's "Earth data & insights" panel.
 * The land-use and soil insights are plot-level numbers (no raster is drawn),
 * so the panel shows them as short lines under their toggles.
 */
import type { Analysis, TreeInventory } from '@/types/api';
import { LANDCOVER_STYLES } from './landcover';

export interface LandUseShare {
  /** i18n key such as `landcover.cropland`, or null for a class we have no key for. */
  key: string | null;
  /** Class name as sent by the API (fallback label). */
  name: string;
  share: number;
}

/** The largest land-cover classes inside the plot, largest first. */
export function landUseShares(analysis: Analysis | null | undefined, max = 3): LandUseShare[] {
  const classes = analysis?.landcover?.classes ?? [];
  return [...classes]
    .filter((c) => Number.isFinite(c.share) && c.share > 0)
    .sort((a, b) => b.share - a.share)
    .slice(0, Math.max(0, max))
    .map((c) => ({
      key: LANDCOVER_STYLES.find((s) => s.code === c.code)?.key ?? null,
      name: c.name,
      share: c.share,
    }));
}

export interface SoilInsight {
  socGPerKg: number | null;
  climateZone: string | null;
  climateZoneLabel: string | null;
}

/** Soil organic carbon (0–30 cm) and the climate zone used by the estimate. */
export function soilInsight(analysis: Analysis | null | undefined): SoilInsight | null {
  if (!analysis) return null;
  const soc = analysis.soil?.soc_0_30cm_g_per_kg;
  const zone = analysis.climate?.zone ?? null;
  if (soc == null && !zone) return null;
  return {
    socGPerKg: soc == null || !Number.isFinite(soc) ? null : soc,
    climateZone: zone,
    climateZoneLabel: analysis.climate?.zone_label ?? null,
  };
}

/**
 * The tree inventory the app should use: the most recently saved one.
 * The API lists inventories oldest first, and every save of the tree form
 * creates a new version, so the first item is the OLDEST, not the current one.
 */
export function latestInventory(
  items: readonly TreeInventory[] | null | undefined,
): TreeInventory | null {
  if (!items || items.length === 0) return null;
  let latest = items[0];
  for (const item of items) {
    if (Date.parse(item.created_at) >= Date.parse(latest.created_at)) latest = item;
  }
  return latest;
}
