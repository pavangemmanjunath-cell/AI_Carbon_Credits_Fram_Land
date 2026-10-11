/**
 * "Tree cover (AI detected)" — display helpers for `POST /plots/{id}/detect`.
 * The patches, confidences and areas come from the server; this module only
 * shapes them for the map and the one-line summary.
 */
import type { Detection, DetectionPatchProperties } from '@/types/api';

/** Fill opacity grows with confidence: 0.5 → 0.25, 1.0 → 0.6. */
export function confidenceOpacity(confidence: number | null | undefined): number {
  const c = Math.max(0, Math.min(1, Number(confidence ?? 0)));
  return Number((0.1 + c * 0.5).toFixed(3));
}

/** The same rule as a MapLibre expression for the fill layer. */
export const CONFIDENCE_OPACITY_EXPRESSION = [
  'interpolate',
  ['linear'],
  ['coalesce', ['get', 'confidence'], 0],
  0,
  0.1,
  1,
  0.6,
] as const;

export interface DetectionSummary {
  patches: number;
  coveredFraction: number;
  areaHectares: number;
}

export function detectionSummary(detection: Detection | null | undefined): DetectionSummary | null {
  if (!detection) return null;
  return {
    patches: detection.summary.patches ?? detection.features.features.length,
    coveredFraction: detection.summary.covered_fraction,
    areaHectares: detection.summary.area_hectares,
  };
}

export interface PatchInfo {
  confidence: string;
  hectares: number;
}

/** Popup values for one patch: confidence with two decimals and area in hectares. */
export function patchInfo(
  properties: Partial<DetectionPatchProperties> | null | undefined,
): PatchInfo | null {
  if (!properties || properties.confidence == null || properties.area_m2 == null) return null;
  return {
    confidence: Number(properties.confidence).toFixed(2),
    hectares: Number(properties.area_m2) / 10_000,
  };
}
