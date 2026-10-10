import '@testing-library/jest-dom/vitest';
import { afterEach, vi } from 'vitest';
import { cleanup } from '@testing-library/react';
import '@/i18n';

// Node 24's fetch `Request` rejects jsdom's AbortSignal ("Expected signal to be
// an instance of AbortSignal"), which breaks React Router navigations in tests.
// A native AbortController cannot be built inside jsdom, so the jsdom signal is
// dropped; no test relies on cancelling a router Request. (Node 22, used in CI,
// accepted the jsdom signal; dropping it there changes nothing either.)
{
  const NativeRequest = globalThis.Request;
  globalThis.Request = class extends NativeRequest {
    constructor(input: RequestInfo | URL, init?: RequestInit) {
      super(input, init?.signal instanceof AbortSignal ? { ...init, signal: undefined } : init);
    }
  } as typeof Request;
}

// jsdom lacks these browser APIs used by the UI primitives.
if (!HTMLDialogElement.prototype.showModal) {
  HTMLDialogElement.prototype.showModal = function showModal() {
    this.setAttribute('open', '');
  };
  HTMLDialogElement.prototype.close = function close() {
    this.removeAttribute('open');
  };
}
if (!window.matchMedia) {
  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }));
}
class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}
if (!window.ResizeObserver) window.ResizeObserver = ResizeObserverMock as unknown as typeof ResizeObserver;

afterEach(() => cleanup());
