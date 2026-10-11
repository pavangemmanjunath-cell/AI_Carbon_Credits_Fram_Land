/**
 * The only module that knows API URLs. Everything here mirrors
 * docs/architecture/api-contract.md. Components never import this directly;
 * they go through the TanStack Query hooks in `./queries.ts`, which add the
 * demo fallback.
 */
import type {
  Analysis,
  AnalyzeBody,
  AttributionResponse,
  CarbonEstimate,
  CarbonEstimateBody,
  Cube,
  CubeIndex,
  DetectBody,
  Detection,
  ExplainBody,
  FromLineBody,
  FromLineResult,
  FromPointBody,
  FromPointResult,
  ExplainResponse,
  GeocodeResponse,
  Health,
  ImageryProvidersResponse,
  ImportList,
  ImportRecord,
  ImportUploadOptions,
  MarketScenario,
  Methodology,
  ParseCoordinatesBody,
  ParseCoordinatesResult,
  Plot,
  PlotCreateBody,
  PlotList,
  PolicyEligibility,
  ProblemDetails,
  Region,
  ReportBody,
  ReportHandle,
  ReverseGeocodeResponse,
  Simulation,
  SimulateBody,
  Species,
  TreeInventory,
  TreeInventoryBody,
  TreeInventoryList,
} from '@/types/api';

const DEFAULT_BASE_URL = 'http://localhost:8000/api/v1';

export function apiBaseUrl(): string {
  const raw = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim();
  return (raw && raw.length > 0 ? raw : DEFAULT_BASE_URL).replace(/\/+$/, '');
}

function apiKey(): string | undefined {
  const key = (import.meta.env.VITE_API_KEY as string | undefined)?.trim();
  return key && key.length > 0 ? key : undefined;
}

/** Raised for any non-2xx response; carries the RFC 7807 problem fields. */
export class ApiError extends Error {
  readonly status: number;
  readonly title: string;
  readonly detail?: string;
  readonly type?: string;
  readonly instance?: string;
  readonly problem?: ProblemDetails;

  constructor(status: number, problem: ProblemDetails | undefined, fallbackMessage: string) {
    const title = problem?.title ?? fallbackMessage;
    super(problem?.detail ? `${title}: ${problem.detail}` : title);
    this.name = 'ApiError';
    this.status = status;
    this.title = title;
    this.detail = problem?.detail;
    this.type = problem?.type;
    this.instance = problem?.instance;
    this.problem = problem;
  }
}

/** Raised when the server could not be reached at all (DNS, refused, CORS, timeout). */
export class NetworkError extends Error {
  override readonly cause?: unknown;
  constructor(message: string, cause?: unknown) {
    super(message);
    this.name = 'NetworkError';
    this.cause = cause;
  }
}

/** True when the failure means "the API is not there" rather than "the request was wrong". */
export function isUnreachable(error: unknown): boolean {
  if (error instanceof NetworkError) return true;
  if (error instanceof ApiError)
    return error.status === 502 || error.status === 503 || error.status === 504;
  return false;
}

export function buildUrl(
  path: string,
  params?: Record<string, string | number | undefined>,
): string {
  const url = new URL(`${apiBaseUrl()}${path.startsWith('/') ? path : `/${path}`}`);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== '') url.searchParams.set(key, String(value));
    }
  }
  return url.toString();
}

export async function parseProblem(response: Response): Promise<ProblemDetails | undefined> {
  const contentType = response.headers.get('content-type') ?? '';
  if (!contentType.includes('json')) return undefined;
  try {
    const body = (await response.json()) as unknown;
    if (body && typeof body === 'object') return body as ProblemDetails;
  } catch {
    /* body was not JSON after all */
  }
  return undefined;
}

export interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  body?: unknown;
  params?: Record<string, string | number | undefined>;
  signal?: AbortSignal;
  /** Expected response kind; `text` is used for rendered reports. */
  as?: 'json' | 'text';
  timeoutMs?: number;
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, params, signal, as = 'json', timeoutMs = 20_000 } = options;
  const headers: Record<string, string> = {
    Accept: as === 'json' ? 'application/json, application/problem+json' : 'text/html, */*',
  };
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  const key = apiKey();
  if (key) headers['X-API-Key'] = key;

  const controller = new AbortController();
  const timer = setTimeout(
    () => controller.abort(new DOMException('Request timed out', 'TimeoutError')),
    timeoutMs,
  );
  const onOuterAbort = () => controller.abort(signal?.reason);
  signal?.addEventListener('abort', onOuterAbort, { once: true });

  let response: Response;
  try {
    response = await fetch(buildUrl(path, params), {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: controller.signal,
    });
  } catch (cause) {
    // Cancelled by the caller (page left, query superseded, React StrictMode's
    // double mount): not a connectivity failure, so it must not flip the app
    // into offline/demo mode. A timeout still counts as unreachable.
    if (signal?.aborted) throw new DOMException('Request cancelled', 'AbortError');
    throw new NetworkError(`Could not reach the API at ${apiBaseUrl()}`, cause);
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener('abort', onOuterAbort);
  }

  if (!response.ok) {
    const problem = await parseProblem(response);
    throw new ApiError(
      response.status,
      problem,
      `${response.status} ${response.statusText || 'Request failed'}`,
    );
  }
  if (response.status === 204) return undefined as T;
  if (as === 'text') return (await response.text()) as T;
  return (await response.json()) as T;
}

function problemFromText(contentType: string | null, text: string): ProblemDetails | undefined {
  if (!contentType?.includes('json') || !text) return undefined;
  try {
    const body = JSON.parse(text) as unknown;
    return body && typeof body === 'object' ? (body as ProblemDetails) : undefined;
  } catch {
    return undefined;
  }
}

export interface UploadOptions {
  onProgress?: (fraction: number) => void;
  signal?: AbortSignal;
  timeoutMs?: number;
}

/**
 * Multipart POST with upload progress. `fetch` cannot report upload progress,
 * so this uses XMLHttpRequest; errors map to the same ApiError / NetworkError
 * classes as `request`. A cancelled upload rejects with an `AbortError`.
 */
export function upload<T>(path: string, form: FormData, options: UploadOptions = {}): Promise<T> {
  const { onProgress, signal, timeoutMs = 300_000 } = options;
  return new Promise<T>((resolve, reject) => {
    if (signal?.aborted) {
      reject(new DOMException('Upload cancelled', 'AbortError'));
      return;
    }
    const xhr = new XMLHttpRequest();
    xhr.open('POST', buildUrl(path));
    xhr.timeout = timeoutMs;
    xhr.setRequestHeader('Accept', 'application/json, application/problem+json');
    const key = apiKey();
    if (key) xhr.setRequestHeader('X-API-Key', key);
    const onAbort = () => xhr.abort();
    signal?.addEventListener('abort', onAbort, { once: true });
    const done = () => signal?.removeEventListener('abort', onAbort);
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable && event.total > 0) onProgress?.(event.loaded / event.total);
    };
    xhr.onload = () => {
      done();
      if (xhr.status >= 200 && xhr.status < 300) {
        onProgress?.(1);
        if (xhr.status === 204 || !xhr.responseText) {
          resolve(undefined as T);
          return;
        }
        try {
          resolve(JSON.parse(xhr.responseText) as T);
        } catch (cause) {
          reject(
            new ApiError(
              xhr.status,
              { title: 'Invalid response', detail: String(cause) },
              'Invalid response',
            ),
          );
        }
        return;
      }
      const problem = problemFromText(xhr.getResponseHeader('content-type'), xhr.responseText);
      reject(
        new ApiError(xhr.status, problem, `${xhr.status} ${xhr.statusText || 'Request failed'}`),
      );
    };
    xhr.onerror = () => {
      done();
      reject(new NetworkError(`Could not reach the API at ${apiBaseUrl()}`));
    };
    xhr.ontimeout = () => {
      done();
      reject(
        new ApiError(
          408,
          {
            title: 'Upload timed out',
            status: 408,
            detail: 'The server did not answer in time. Try a smaller file.',
          },
          'Upload timed out',
        ),
      );
    };
    xhr.onabort = () => {
      done();
      reject(new DOMException('Upload cancelled', 'AbortError'));
    };
    xhr.send(form);
  });
}

/** `POST /imports` form fields (contract §v0.2 Imports). */
export function importFormData(file: File, options: ImportUploadOptions = {}): FormData {
  const form = new FormData();
  form.append('file', file, file.name);
  if (options.plotId) form.append('plot_id', options.plotId);
  form.append('purpose', options.purpose ?? 'auto');
  form.append('run_detection', String(options.runDetection ?? true));
  return form;
}

// ─── Typed endpoints (one function per contract entry) ──────────────────────

export const api = {
  health: (signal?: AbortSignal) => request<Health>('/health', { signal, timeoutMs: 6_000 }),
  regions: () => request<Region[]>('/regions'),
  geocode: (q: string, country?: string, signal?: AbortSignal) =>
    request<GeocodeResponse>('/geocode', { params: { q, country }, signal }),
  reverseGeocode: (lat: number, lon: number) =>
    request<ReverseGeocodeResponse>('/reverse-geocode', { params: { lat, lon } }),
  species: (country?: string) => request<Species[]>('/species', { params: { country } }),
  methodologies: () => request<Methodology[]>('/methodologies'),
  attribution: () => request<AttributionResponse>('/attribution'),

  listPlots: () => request<PlotList>('/plots'),
  getPlot: (plotId: string) => request<Plot>(`/plots/${encodeURIComponent(plotId)}`),
  createPlot: (body: PlotCreateBody) => request<Plot>('/plots', { method: 'POST', body }),
  deletePlot: (plotId: string) =>
    request<void>(`/plots/${encodeURIComponent(plotId)}`, { method: 'DELETE' }),

  analyze: (plotId: string, body: AnalyzeBody = {}) =>
    request<Analysis>(`/plots/${encodeURIComponent(plotId)}/analyze`, {
      method: 'POST',
      body,
      timeoutMs: 60_000,
    }),
  cube: (plotId: string, index: CubeIndex = 'ndvi', months = 36) =>
    request<Cube>(`/plots/${encodeURIComponent(plotId)}/cube`, {
      params: { index, months },
      timeoutMs: 60_000,
    }),

  listTrees: (plotId: string) =>
    request<TreeInventoryList>(`/plots/${encodeURIComponent(plotId)}/trees`),
  createTrees: (plotId: string, body: TreeInventoryBody) =>
    request<TreeInventory>(`/plots/${encodeURIComponent(plotId)}/trees`, { method: 'POST', body }),

  carbonEstimate: (plotId: string, body: CarbonEstimateBody = {}) =>
    request<CarbonEstimate>(`/plots/${encodeURIComponent(plotId)}/carbon-estimate`, {
      method: 'POST',
      body,
    }),
  policyEligibility: (plotId: string, activity = 'tree_plantation') =>
    request<PolicyEligibility>(`/plots/${encodeURIComponent(plotId)}/policy-eligibility`, {
      params: { activity },
    }),
  marketScenario: (plotId: string, estimateId?: string) =>
    request<MarketScenario>(`/plots/${encodeURIComponent(plotId)}/market-scenario`, {
      params: { estimate_id: estimateId },
    }),

  createReport: (plotId: string, body: ReportBody) =>
    request<ReportHandle>(`/plots/${encodeURIComponent(plotId)}/report`, {
      method: 'POST',
      body,
      timeoutMs: 60_000,
    }),
  /** `url` comes from the report handle and is relative to the API origin (e.g. `/api/v1/reports/RPT-…`). */
  fetchReportDocument: (reportUrl: string) => {
    const base = new URL(apiBaseUrl());
    const absolute = reportUrl.startsWith('http')
      ? reportUrl
      : new URL(reportUrl, base.origin).toString();
    const path = absolute.startsWith(apiBaseUrl()) ? absolute.slice(apiBaseUrl().length) : null;
    if (path) return request<string>(path, { as: 'text', timeoutMs: 60_000 });
    return fetch(absolute).then(async (r) => {
      if (!r.ok) throw new ApiError(r.status, await parseProblem(r), `${r.status} ${r.statusText}`);
      return r.text();
    });
  },

  simulate: (body: SimulateBody, signal?: AbortSignal) =>
    request<Simulation>('/simulate', { method: 'POST', body, signal }),
  explain: (body: ExplainBody) => request<ExplainResponse>('/explain', { method: 'POST', body }),

  // ─── v0.2 · geometry helpers (pure calculations, nothing stored) ─────────
  geometryFromPoint: (body: FromPointBody, signal?: AbortSignal) =>
    request<FromPointResult>('/geometry/from-point', { method: 'POST', body, signal }),
  geometryFromLine: (body: FromLineBody, signal?: AbortSignal) =>
    request<FromLineResult>('/geometry/from-line', { method: 'POST', body, signal }),
  parseCoordinates: (body: ParseCoordinatesBody, signal?: AbortSignal) =>
    request<ParseCoordinatesResult>('/geometry/parse-coordinates', {
      method: 'POST',
      body,
      signal,
    }),

  // ─── v0.2 · imports ──────────────────────────────────────────────────────
  uploadImport: (file: File, options: ImportUploadOptions = {}) =>
    upload<ImportRecord>('/imports', importFormData(file, options), {
      onProgress: options.onProgress,
      signal: options.signal,
    }),
  listImports: (plotId?: string) =>
    request<ImportList>('/imports', { params: { plot_id: plotId } }),
  getImport: (importId: string) =>
    request<ImportRecord>(`/imports/${encodeURIComponent(importId)}`),
  deleteImport: (importId: string) =>
    request<void>(`/imports/${encodeURIComponent(importId)}`, { method: 'DELETE' }),

  // ─── v0.2 · detection ────────────────────────────────────────────────────
  detect: (plotId: string, body: DetectBody) =>
    request<Detection>(`/plots/${encodeURIComponent(plotId)}/detect`, {
      method: 'POST',
      body,
      timeoutMs: 60_000,
    }),
  latestDetection: (plotId: string) =>
    request<Detection>(`/plots/${encodeURIComponent(plotId)}/detections`),

  // ─── v0.2 · imagery ──────────────────────────────────────────────────────
  imageryProviders: (country?: string) =>
    request<ImageryProvidersResponse>('/imagery/providers', { params: { country } }),
};

export type Api = typeof api;
