import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { resetUiStore, useUiStore } from '@/store/uiStore';
import { ApiError, api, importFormData, isUnreachable, NetworkError, request } from './api';
import { client } from './client';
import { FeatureNeedsApiError } from './demoFallback';

const problem = { type: 'https://agricarbon-atlas.org/problems/plot-not-found', title: 'Not Found', status: 404, detail: 'Plot X was not found.', instance: '/api/v1/plots/X' };

describe('api client', () => {
  afterEach(() => vi.restoreAllMocks());

  it('parses RFC 7807 problems into ApiError', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify(problem), { status: 404, headers: { 'content-type': 'application/problem+json' } }));
    await expect(api.getPlot('X')).rejects.toMatchObject({ name: 'ApiError', status: 404, detail: 'Plot X was not found.' });
  });

  it('wraps connectivity failures in NetworkError and flags them unreachable', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('Failed to fetch'));
    const error = await api.health().catch((e: unknown) => e);
    expect(error).toBeInstanceOf(NetworkError);
    expect(isUnreachable(error)).toBe(true);
    expect(isUnreachable(new ApiError(422, undefined, 'x'))).toBe(false);
    expect(isUnreachable(new ApiError(503, undefined, 'x'))).toBe(true);
  });

  it('treats a request cancelled by the caller as cancelled, not as the API being offline', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(
      (_url, init) =>
        new Promise((_resolve, reject) => {
          init?.signal?.addEventListener('abort', () => reject(new DOMException('aborted', 'AbortError')));
        }),
    );
    const outer = new AbortController();
    const pending = request('/plots', { signal: outer.signal }).catch((e: unknown) => e);
    outer.abort();
    const error = await pending;
    expect(error).toMatchObject({ name: 'AbortError' });
    expect(isUnreachable(error)).toBe(false);
  });

  it('sends JSON bodies and reads text responses', async () => {
    const spy = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('<html></html>', { status: 200, headers: { 'content-type': 'text/html' } }));
    const text = await request<string>('/reports/R', { as: 'text' });
    expect(text).toBe('<html></html>');
    expect(spy).toHaveBeenCalledOnce();
    const init = spy.mock.calls[0][1] as RequestInit;
    expect(init.method).toBe('GET');
  });
});

// ─── v0.2 additions ──────────────────────────────────────────────────────────

class FakeXhr {
  static last: FakeXhr | null = null;
  method = '';
  url = '';
  headers: Record<string, string> = {};
  body: unknown = null;
  status = 0;
  statusText = '';
  responseText = '';
  timeout = 0;
  upload: { onprogress: ((event: { lengthComputable: boolean; loaded: number; total: number }) => void) | null } = { onprogress: null };
  onload: (() => void) | null = null;
  onerror: (() => void) | null = null;
  ontimeout: (() => void) | null = null;
  onabort: (() => void) | null = null;
  private responseHeaders: Record<string, string> = {};
  constructor() {
    FakeXhr.last = this;
  }
  open(method: string, url: string) {
    this.method = method;
    this.url = url;
  }
  setRequestHeader(key: string, value: string) {
    this.headers[key] = value;
  }
  getResponseHeader(key: string) {
    return this.responseHeaders[key.toLowerCase()] ?? null;
  }
  send(body: unknown) {
    this.body = body;
  }
  abort() {
    this.onabort?.();
  }
  respond(status: number, body: unknown, contentType = 'application/json') {
    this.status = status;
    this.responseText = JSON.stringify(body);
    this.responseHeaders['content-type'] = contentType;
    this.onload?.();
  }
}

describe('v0.2 endpoints', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    FakeXhr.last = null;
  });

  it('builds the POST /imports form fields', () => {
    const file = new File(['{}'], 'field.geojson');
    const form = importFormData(file, { plotId: 'PLT-1', runDetection: false });
    expect((form.get('file') as File).name).toBe('field.geojson');
    expect(form.get('plot_id')).toBe('PLT-1');
    expect(form.get('purpose')).toBe('auto');
    expect(form.get('run_detection')).toBe('false');
    const noPlot = importFormData(file);
    expect(noPlot.get('plot_id')).toBeNull();
    expect(noPlot.get('run_detection')).toBe('true');
  });

  it('uploads with progress and returns the ImportRecord', async () => {
    vi.stubGlobal('XMLHttpRequest', FakeXhr);
    const progress: number[] = [];
    const pending = api.uploadImport(new File(['x'], 'orchard.laz'), { plotId: 'PLT-1', onProgress: (p) => progress.push(p) });
    const xhr = FakeXhr.last!;
    expect(xhr.method).toBe('POST');
    expect(xhr.url).toMatch(/\/imports$/);
    expect(xhr.body).toBeInstanceOf(FormData);
    xhr.upload.onprogress?.({ lengthComputable: true, loaded: 50, total: 100 });
    xhr.respond(201, { import_id: 'IMP-1', status: 'ready' });
    await expect(pending).resolves.toMatchObject({ import_id: 'IMP-1' });
    expect(progress).toEqual([0.5, 1]);
  });

  it('maps upload problems to ApiError with the RFC 7807 detail', async () => {
    vi.stubGlobal('XMLHttpRequest', FakeXhr);
    const pending = api.uploadImport(new File(['x'], 'scan.e57'));
    FakeXhr.last!.respond(415, { title: 'Unsupported Media Type', status: 415, detail: 'Convert to LAS/LAZ with CloudCompare or PDAL.' }, 'application/problem+json');
    await expect(pending).rejects.toMatchObject({ name: 'ApiError', status: 415, detail: 'Convert to LAS/LAZ with CloudCompare or PDAL.' });
  });

  it('reports network failures and cancellations', async () => {
    vi.stubGlobal('XMLHttpRequest', FakeXhr);
    const failing = api.uploadImport(new File(['x'], 'a.kml'));
    FakeXhr.last!.onerror?.();
    await expect(failing).rejects.toBeInstanceOf(NetworkError);
    const controller = new AbortController();
    const cancelled = api.uploadImport(new File(['x'], 'a.kml'), { signal: controller.signal });
    controller.abort();
    await expect(cancelled).rejects.toMatchObject({ name: 'AbortError' });
  });

  it('calls the geometry, detection and imagery endpoints of the contract', async () => {
    const spy = vi.spyOn(globalThis, 'fetch').mockImplementation(async () => new Response('{}', { status: 200, headers: { 'content-type': 'application/json' } }));
    await api.geometryFromPoint({ lat: 13.29, lon: 77.53, area: { value: 2, unit: 'ac' } });
    await api.geometryFromLine({ line: { type: 'LineString', coordinates: [[0, 0], [1, 1]] }, width_m: 4, spacing_m: 5 });
    await api.parseCoordinates({ text: '13.29, 77.53' });
    await api.detect('PLT-1', { target: 'tree-cover', min_confidence: 0.5 });
    await api.latestDetection('PLT-1');
    await api.imageryProviders('IN');
    await api.listImports('PLT-1');
    const calls = spy.mock.calls.map(([url, init]) => `${(init as RequestInit).method} ${new URL(String(url)).pathname}${new URL(String(url)).search}`);
    expect(calls).toEqual([
      'POST /api/v1/geometry/from-point',
      'POST /api/v1/geometry/from-line',
      'POST /api/v1/geometry/parse-coordinates',
      'POST /api/v1/plots/PLT-1/detect',
      'GET /api/v1/plots/PLT-1/detections',
      'GET /api/v1/imagery/providers?country=IN',
      'GET /api/v1/imports?plot_id=PLT-1',
    ]);
  });
});

describe('client fallbacks for v0.2', () => {
  beforeEach(() => resetUiStore());
  afterEach(() => vi.restoreAllMocks());

  it('computes geometry helpers in the browser when the API is offline, labelled as such', async () => {
    useUiStore.getState().setApiStatus('offline');
    const result = await client.geometryFromPoint({ lat: 13.29, lon: 77.53, area: { value: 2, unit: 'ha' } });
    expect(result.area_hectares).toBeCloseTo(2, 2);
    expect(result.method).toMatch(/^offline/);
    await expect(client.geometryFromPoint({ lat: 13.29, lon: 77.53, area: { value: 0, unit: 'ha' } })).rejects.toMatchObject({ status: 422 });
  });

  it('answers server-only features with a friendly "needs the API" error offline', async () => {
    useUiStore.getState().setApiStatus('offline');
    await expect(client.uploadImport(new File(['x'], 'a.geojson'))).rejects.toBeInstanceOf(FeatureNeedsApiError);
    await expect(client.imageryProviders('IN')).rejects.toBeInstanceOf(FeatureNeedsApiError);
    await expect(client.latestOrDetect('PLT-1')).rejects.toBeInstanceOf(FeatureNeedsApiError);
  });

  it('runs a detection when the plot has none stored yet', async () => {
    const detection = { detection_id: 'DET-1', plot_id: 'PLT-1' };
    const spy = vi.spyOn(globalThis, 'fetch').mockImplementation(async (_url, init) => {
      if ((init as RequestInit).method === 'GET') {
        return new Response(JSON.stringify({ title: 'Not Found', status: 404 }), { status: 404, headers: { 'content-type': 'application/problem+json' } });
      }
      return new Response(JSON.stringify(detection), { status: 200, headers: { 'content-type': 'application/json' } });
    });
    await expect(client.latestOrDetect('PLT-1')).resolves.toMatchObject({ detection_id: 'DET-1' });
    expect(spy).toHaveBeenCalledTimes(2);
    expect(JSON.parse(String((spy.mock.calls[1][1] as RequestInit).body))).toEqual({ target: 'tree-cover', min_confidence: 0.5 });
  });
});
