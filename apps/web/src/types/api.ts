/**
 * TypeScript mirror of docs/architecture/api-contract.md (`/api/v1`).
 * Field names stay snake_case exactly as they travel on the wire — there is
 * deliberately no renaming layer between the back end and the UI.
 */

export type CountryCode = 'IN' | 'US' | 'EU' | (string & {});
export type ApiMode = 'demo' | 'live';
export type Confidence = 'low' | 'medium' | 'high';
export type VerificationStatus = 'verified' | 'pending' | 'assumption';

// ─── Shared objects ──────────────────────────────────────────────────────────

export interface ProvenanceSource {
  id: string;
  name: string;
  version?: string | null;
  license: string;
  attribution: string;
  url?: string | null;
  accessed_at?: string | null;
  scene_ids?: string[];
  acquisition_dates?: string[];
}

export interface Provenance {
  generated_at: string;
  api_version: string;
  mode: ApiMode;
  sources: ProvenanceSource[];
  model?: { id: string; version: string } | null;
  parameter_set?: { id: string; version: string; verification_status: string } | null;
  notes?: string[];
}

export interface Range {
  low: number;
  central: number;
  high: number;
  unit: string;
}

export interface Reference {
  title: string;
  url?: string;
}

export interface LatLon {
  lat: number;
  lon: number;
}

export interface PolygonGeometry {
  type: 'Polygon';
  coordinates: number[][][];
}

export interface PointGeometry {
  type: 'Point';
  coordinates: [number, number];
}

export interface LineStringGeometry {
  type: 'LineString';
  coordinates: number[][];
}

/** RFC 7807 problem document. */
export interface ProblemDetails {
  type?: string;
  title?: string;
  status?: number;
  detail?: string;
  instance?: string;
  [extra: string]: unknown;
}

// ─── GET /health ─────────────────────────────────────────────────────────────

export interface Health {
  status: string;
  version: string;
  mode: ApiMode;
  time: string;
}

// ─── GET /regions ────────────────────────────────────────────────────────────

export interface RegionProgramme {
  id: string;
  name: string;
  authority: string;
  kind: string;
  url: string;
}

export interface Region {
  id: CountryCode;
  name: string;
  calling_code: string | null;
  currency: string;
  currency_symbol: string;
  units: { area: 'hectare' | 'acre'; area_secondary: 'hectare' | 'acre' };
  languages: string[];
  default_center: LatLon;
  default_zoom: number;
  bbox: [number, number, number, number];
  programmes: RegionProgramme[];
}

// ─── GET /geocode · GET /reverse-geocode ─────────────────────────────────────

export interface GeocodeResult {
  label: string;
  lat: number;
  lon: number;
  bbox?: [number, number, number, number];
  admin?: { country?: string; state?: string; district?: string };
}

export interface GeocodeResponse {
  results: GeocodeResult[];
  provider: string;
  attribution: string;
}

export interface ReverseGeocodeResponse {
  country: string;
  state?: string;
  district?: string;
  label: string;
  provider: string;
  attribution: string;
}

// ─── GET /species ────────────────────────────────────────────────────────────

export interface SourcedValue<T = number> {
  value: T;
  source: string;
  verification_status: VerificationStatus | string;
}

export interface Species {
  id: string;
  scientific_name: string;
  common_name: string;
  group: string;
  regions: CountryCode[];
  suitable_climate_zones: string[];
  reference_density_per_ha: SourcedValue;
  max_density_per_ha: number;
  maturity_years: number;
  wood_density_g_cm3: SourcedValue;
  increment_multiplier?: SourcedValue;
  typical_height_m_at_maturity?: SourcedValue;
  allometry?: string;
  notes?: string;
}

// ─── GET /methodologies · GET /attribution ───────────────────────────────────

export interface Methodology {
  id: string;
  name: string;
  kind: string;
  regions: string[];
  url: string;
  status: string;
  notes?: string;
}

export interface AttributionItem {
  id: string;
  text: string;
  url?: string;
  license?: string;
}

export interface AttributionResponse {
  items: AttributionItem[];
}

// ─── Plots ───────────────────────────────────────────────────────────────────

export type PlotSource =
  | 'manual-drawing'
  | 'upload'
  | 'import'
  | 'pin-and-area'
  | 'tree-line'
  | 'coordinates'
  | 'qgis-plugin'
  | 'api'
  | 'synthetic-demo';

/** v0.2: boundaries built from a pin + size or a tree line are `approximate`. */
export type BoundaryQuality = 'exact' | 'approximate';

export interface PlotCreateBody {
  name: string;
  country?: CountryCode;
  source: PlotSource;
  geometry: PolygonGeometry;
  /** Defaults to `exact` on the server. */
  boundary_quality?: BoundaryQuality;
}

export interface Plot {
  plot_id: string;
  name: string;
  country: CountryCode;
  region?: string | null;
  /** Returned only to the owner. */
  geometry?: PolygonGeometry;
  area_hectares: number;
  area_acres: number;
  perimeter_m: number;
  /** Returned only to the owner. */
  centroid?: LatLon;
  public_centroid: LatLon;
  source: PlotSource;
  /** v0.2 field; absent on older records, which are treated as `exact`. */
  boundary_quality?: BoundaryQuality;
  privacy: 'private' | 'generalized-public';
  created_at: string;
  updated_at?: string | null;
}

export interface PlotList {
  items: Plot[];
}

// ─── POST /plots/{id}/analyze ────────────────────────────────────────────────

export type AnalysisLayer = 'landcover' | 'vegetation' | 'climate' | 'soil' | 'terrain';

export interface AnalyzeBody {
  layers?: AnalysisLayer[];
  years?: number[];
}

export interface LandcoverClass {
  code: number;
  name: string;
  share: number;
  area_ha: number;
}

export interface LandcoverBlock {
  dataset: string;
  version: string;
  resolution_m: number;
  classes: LandcoverClass[];
  tree_cover_share: number;
  cropland_share: number;
  provenance: Provenance;
}

export type NdviClass = 'sparse' | 'moderate' | 'healthy';
export type NdmiClass = 'dry' | 'moderate' | 'moist';

export interface IndexObservation<C extends string = string> {
  value: number;
  class: C;
  date: string;
  scene_id: string;
}

export interface VegetationTimePoint {
  date: string;
  ndvi: number;
  ndmi?: number;
  cloud_cover?: number;
  scene_id?: string;
}

export interface VegetationBlock {
  indices: {
    ndvi: IndexObservation<NdviClass>;
    ndmi?: IndexObservation<NdmiClass>;
  };
  time_series: VegetationTimePoint[];
  trend: { start: string; end: string; change_pct: number; statement: string };
  provenance: Provenance;
}

export interface ClimateBlock {
  zone: string;
  zone_label: string;
  zone_source?: string;
  mean_annual_temp_c: number | null;
  annual_precip_mm: number | null;
  elevation_m: number | null;
  provenance: Provenance;
}

export interface SoilBlock {
  soc_0_30cm_g_per_kg: number;
  provenance: Provenance;
}

export interface Analysis {
  plot_id: string;
  mode: ApiMode;
  landcover?: LandcoverBlock;
  vegetation?: VegetationBlock;
  climate?: ClimateBlock;
  soil?: SoilBlock;
  data_quality: { warnings: string[] };
  generated_at: string;
}

// ─── GET /plots/{id}/cube ────────────────────────────────────────────────────

export type CubeIndex = 'ndvi' | 'ndmi' | 'ndre';

export interface CubeGrid {
  rows: number;
  cols: number;
  cell_size_m: number;
  bbox: [number, number, number, number];
  crs: string;
}

export interface CubeTimeStats {
  time: string;
  mean: number;
  min: number;
  max: number;
  valid_share: number;
}

export interface CubeProvenance {
  source: string;
  composite: string;
  cloud_mask: string;
  aggregation: string;
  scene_ids: string[];
}

export interface Cube {
  plot_id: string;
  index: CubeIndex;
  mode: ApiMode;
  grid: CubeGrid;
  times: string[];
  /** rows × cols; 1 inside the polygon, 0 outside. */
  mask: number[][];
  /** times × rows × cols; null outside the polygon or where cloud-masked. */
  values: (number | null)[][][];
  stats_per_time: CubeTimeStats[];
  provenance: CubeProvenance;
}

// ─── Trees ───────────────────────────────────────────────────────────────────

export type MeasurementSource =
  | 'user-reported'
  | 'satellite-derived'
  | 'government-data'
  | 'field-measured'
  | 'model-estimated';

export interface TreeInventoryBody {
  species_id: string;
  tree_count: number;
  plantation_year: number;
  average_dbh_cm: number | null;
  average_height_m: number | null;
  survival_rate: number | null;
  measurement_source: MeasurementSource;
}

export interface DataQualityField {
  name: string;
  status: 'supplied' | 'missing';
}

export interface TreeInventory {
  inventory_id: string;
  plot_id: string;
  species: { id: string; scientific_name: string; common_name: string };
  tree_count: number;
  density_per_ha: number;
  plantation_year: number;
  age_years: number;
  average_dbh_cm: number | null;
  average_height_m: number | null;
  survival_rate: number | null;
  measurement_source: MeasurementSource;
  data_quality: { fields: DataQualityField[]; confidence: Confidence };
  created_at: string;
}

export interface TreeInventoryList {
  items: TreeInventory[];
}

// ─── Carbon estimate ─────────────────────────────────────────────────────────

export interface CarbonEstimateBody {
  inventory_id?: string;
  model?: string;
}

export interface AnnualPoint {
  year: number;
  age: number;
  low: number;
  central: number;
  high: number;
  cum_low: number;
  cum_central: number;
  cum_high: number;
}

export interface ParameterUsed {
  name: string;
  value: number | string;
  unit: string;
  source: string;
  verification_status: VerificationStatus;
}

export interface EvidenceItem {
  id: string;
  label: string;
  weight?: number;
}

export interface Readiness {
  score: number;
  grade: Confidence;
  present_evidence: EvidenceItem[];
  missing_evidence: EvidenceItem[];
}

export interface CarbonEstimate {
  estimate_id: string;
  plot_id: string;
  inventory_id: string | null;
  model: { id: string; version: string; tier?: string };
  methodology: { id: string; name: string; references?: Reference[] };
  estimate: Range;
  stock?: Range;
  components?: Record<string, number>;
  annual_series: AnnualPoint[];
  parameters_used: ParameterUsed[];
  confidence: Confidence;
  certified: false;
  disclaimer: string;
  readiness: Readiness;
  provenance: Provenance;
  generated_at: string;
}

// ─── Policy eligibility ──────────────────────────────────────────────────────

export type PolicyStatus =
  | 'potentially_applicable'
  | 'requires_assessment'
  | 'requires_methodology_assessment'
  | 'requires_certification'
  | 'not_applicable'
  | 'unknown';

export interface PolicyProgramme {
  id: string;
  name: string;
  authority: string;
  kind: string;
  status: PolicyStatus;
  requirements: string[];
  notes?: string[];
  references: Reference[];
  distinct_from?: string[];
  reason?: string;
}

export interface PolicyEligibility {
  country: CountryCode;
  activity: string;
  disclaimer: string;
  programmes: PolicyProgramme[];
}

// ─── Market scenario ─────────────────────────────────────────────────────────

export interface ValuePerYear {
  low: number;
  central: number;
  high: number;
}

export interface MarketScenarioEntry {
  id: 'low' | 'reference' | 'high' | (string & {});
  price_per_tco2e: number;
  value_per_year: ValuePerYear;
}

export interface OtherIncomeItem {
  id: string;
  label: string;
  value: number | null;
  unit: string;
  source: string;
}

export interface MarketScenario {
  currency: string;
  currency_symbol: string;
  scenarios: MarketScenarioEntry[];
  basis: { source: string; as_of: string; note: string };
  other_income: OtherIncomeItem[];
  disclaimer: string;
}

// ─── Reports ─────────────────────────────────────────────────────────────────

export type ReportFormat = 'html' | 'json' | 'markdown' | 'pdf';

export interface ReportBody {
  format: ReportFormat;
  language: string;
  estimate_id?: string;
}

export interface ReportHandle {
  report_id: string;
  format: ReportFormat;
  url: string;
  generated_at: string;
}

// ─── Simulation ──────────────────────────────────────────────────────────────

export interface SimulateBody {
  country: CountryCode;
  species_id: string;
  tree_count: number;
  planting_year: number;
  horizon_years: number;
  /** Omit to use the engine's configured default (reported with its source). */
  survival_rate?: number;
  area_hectares: number;
  lat?: number;
  lon?: number;
  /** Your own costs (region currency). The platform has no built-in cost values. */
  costs?: CostInputs;
}

export interface CostInputs {
  sapling_per_tree?: number | null;
  planting_per_tree?: number | null;
  maintenance_per_ha_per_year?: number | null;
  monitoring_per_year?: number | null;
}

/** `cost_scenario` of POST /simulate — undiscounted bookkeeping on your costs; never revenue. */
export interface CostScenario {
  currency: string;
  horizon_years: number;
  inputs: CostInputs;
  not_entered: (keyof CostInputs)[];
  establishment: number;
  maintenance_over_horizon: number;
  monitoring_over_horizon: number;
  total_cost: number;
  removal_over_horizon_tco2e: { low: number; central: number; high: number };
  break_even_price_per_tco2e: { low: number | null; central: number | null; high: number | null };
  price_scenarios: {
    id: string;
    price_per_tco2e: number;
    indicative_value_over_horizon: number;
    share_of_costs_covered_pct: number | null;
  }[];
  discounted: false;
  certified: false;
  disclaimer: string;
}

export interface SimulationValueScenario extends MarketScenarioEntry {
  currency: string;
  currency_symbol: string;
}

export interface SimulationProgramme {
  id: string;
  name: string;
  url: string | null;
  status: PolicyStatus;
  kind?: string;
}

export interface SimulationComparison {
  country: CountryCode;
  name?: string;
  climate_zone: string;
  climate_zone_label?: string;
  reference_price_per_tco2e?: number;
  programmes?: SimulationProgramme[];
  annual: Range;
  currency: string;
  currency_symbol: string;
  reference_value_per_year: number;
  programme_summary: string;
  url: string;
}

export interface ShareParams {
  country: CountryCode;
  species: string;
  trees: number;
  year: number;
  horizon: number;
}

export interface Simulation {
  inputs: SimulateBody & { region?: string; density_per_ha?: number };
  region_name?: string;
  currency?: string;
  currency_symbol?: string;
  area_unit?: 'hectare' | 'acre';
  climate_zone: string;
  climate_zone_label: string;
  climate_zone_source?: string;
  stock_now?: Range;
  market_disclaimer?: string;
  parameters_used?: ParameterUsed[];
  annual: Range;
  series: AnnualPoint[];
  value_scenarios: SimulationValueScenario[];
  cost_scenario?: CostScenario | null;
  programmes: SimulationProgramme[];
  comparison: SimulationComparison[];
  confidence: Confidence;
  certified: false;
  disclaimer: string;
  share_params: ShareParams;
  provenance: Provenance;
}

// ─── Explain ─────────────────────────────────────────────────────────────────

/** Derived indicators only — the schema rejects any coordinate-like key. */
export interface ExplainIndicators {
  area_hectares?: number;
  tree_count?: number;
  species?: string;
  ndvi?: number;
  ndvi_trend_pct?: number;
  estimate_central?: number;
  estimate_low?: number;
  estimate_high?: number;
  confidence?: Confidence;
  missing_evidence?: string[];
}

export interface ExplainBody {
  language: string;
  indicators: ExplainIndicators;
}

export interface ExplainResponse {
  text: string;
  provider: 'template' | 'llm' | (string & {});
  privacy_note: string;
}

// ═══ v0.2 additions ══════════════════════════════════════════════════════════

// ─── Geometry helpers (tag `geometry`) — pure calculations, nothing stored ───

/** Area unit accepted by `POST /geometry/from-point`. */
export type AreaInputUnit = 'ha' | 'ac' | 'm2';

export interface FromPointBody {
  lat: number;
  lon: number;
  area: { value: number; unit: AreaInputUnit };
  shape?: 'square' | 'circle';
}

export interface FromPointResult {
  geometry: PolygonGeometry;
  area_hectares: number;
  area_acres: number;
  boundary_quality: BoundaryQuality;
  method: string;
  provenance?: Partial<Provenance>;
}

export interface FromLineBody {
  line: LineStringGeometry;
  /** Strip width used as the plot, 1–50 m (default 4). */
  width_m: number;
  /** Distance between trees, 0.5–50 m (default 5). */
  spacing_m: number;
}

export interface FromLineResult {
  geometry: PolygonGeometry;
  length_m: number;
  area_hectares: number;
  suggested_tree_count: number;
  boundary_quality: BoundaryQuality;
  method: string;
  provenance?: Partial<Provenance>;
}

export interface ParseCoordinatesBody {
  text: string;
}

export type ParsedCoordinatesKind = 'point' | 'polygon' | 'invalid';

export interface ParseCoordinatesResult {
  points: LatLon[];
  kind: ParsedCoordinatesKind;
  geometry: PointGeometry | PolygonGeometry | null;
  area_hectares: number | null;
  warnings: string[];
}

// ─── Imports (tag `imports`) ─────────────────────────────────────────────────

export type ImportKind = 'boundary' | 'tree-points' | 'tree-crowns' | 'point-cloud' | 'unknown';
export type ImportStatus = 'ready' | 'failed';
export type ImportPurpose = 'auto' | 'boundary' | 'trees';

export interface ImportSummary {
  feature_count: number;
  polygon_count: number;
  point_count: number;
  georeferenced: boolean;
  crs: string | null;
}

export interface ImportBoundary {
  geometry: PolygonGeometry;
  area_hectares: number;
  name: string | null;
}

export interface ImportTrees {
  count: number;
  count_in_plot: number | null;
  mean_height_m: number | null;
  median_height_m: number | null;
  p90_height_m: number | null;
  canopy_cover_fraction: number | null;
  confidence_field: string | null;
  min_confidence: number | null;
  method: string;
}

export interface ImportDetection {
  ran: boolean;
  method: string;
  parameters: Record<string, number | string | boolean | null>;
  notes: string[];
}

/** GeoJSON FeatureCollection as returned in `preview` (tree tops, crowns or the boundary). */
export interface PreviewFeatureCollection {
  type: 'FeatureCollection';
  features: {
    type: 'Feature';
    geometry: { type: string; coordinates: unknown } | null;
    properties: Record<string, unknown> | null;
  }[];
}

export interface ImportRecord {
  import_id: string;
  filename: string;
  format: string;
  size_bytes: number;
  created_at: string;
  plot_id: string | null;
  kind: ImportKind;
  status: ImportStatus;
  summary: ImportSummary;
  boundary: ImportBoundary | null;
  trees: ImportTrees | null;
  detection: ImportDetection | null;
  /** Omitted from list responses. */
  preview?: PreviewFeatureCollection | null;
  warnings: string[];
  privacy: 'private';
  provenance?: Partial<Provenance>;
}

export interface ImportList {
  items: ImportRecord[];
}

export interface ImportUploadOptions {
  plotId?: string | null;
  purpose?: ImportPurpose;
  runDetection?: boolean;
  /** Upload progress 0–1. */
  onProgress?: (fraction: number) => void;
  signal?: AbortSignal;
}

// ─── Detection (tag `detection`) ─────────────────────────────────────────────

export interface DetectBody {
  target: 'tree-cover';
  min_confidence?: number;
}

export interface DetectionPatchProperties {
  id: string;
  label: string;
  confidence: number;
  area_m2: number;
  mean_ndvi?: number | null;
}

export interface DetectionFeatureCollection {
  type: 'FeatureCollection';
  features: { type: 'Feature'; geometry: PolygonGeometry; properties: DetectionPatchProperties }[];
}

export interface Detection {
  detection_id: string;
  plot_id: string;
  target: 'tree-cover';
  method: string;
  index: string;
  threshold: number;
  month: string;
  features: DetectionFeatureCollection;
  summary: { patches: number; covered_fraction: number; area_hectares: number };
  limitations: string[];
  created_at: string;
  provenance?: Partial<Provenance>;
}

// ─── Imagery (tag `imagery`) ─────────────────────────────────────────────────

/** Licence answers in config/imagery/providers.yaml: yes / no / read the terms first. */
export type TermsAnswer = boolean | 'allowed' | 'not-allowed' | 'review-terms' | (string & {});

export interface ImageryProvider {
  id: string;
  name: string;
  kind: 'xyz' | (string & {});
  url: string;
  tile_size: number;
  max_zoom: number;
  coverage: { type: 'global' } | { type: 'countries'; countries: string[] };
  resolution: string;
  license: string;
  license_url: string | null;
  attribution: string;
  requires_key: boolean;
  available: boolean;
  unavailable_reason: string | null;
  commercial_use: TermsAnswer;
  analysis_allowed: TermsAnswer;
  open_data: boolean;
  verification_status: VerificationStatus | string;
}

export interface ImageryProvidersResponse {
  recommended: string;
  providers: ImageryProvider[];
  notes?: string;
}
