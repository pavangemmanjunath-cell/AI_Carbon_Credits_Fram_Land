/**
 * Turns any error from the services layer into a sentence for the UI.
 * API problems (RFC 7807) show the server's `detail`; features that only the
 * server can do get a friendly "needs the API" message instead of a stack trace.
 */
import { ApiError, NetworkError } from '@/services/api';
import { FeatureNeedsApiError } from '@/services/demoFallback';

type Translate = (key: string, options?: Record<string, unknown>) => string;

export function isAbortError(error: unknown): boolean {
  return (error instanceof DOMException || error instanceof Error) && error.name === 'AbortError';
}

export function errorMessage(error: unknown, t: Translate): string {
  if (!error) return '';
  if (error instanceof FeatureNeedsApiError) return t('errors.needsApi');
  if (error instanceof ApiError)
    return (
      error.detail ||
      error.title ||
      t('errors.apiError', { status: error.status, title: error.message })
    );
  if (error instanceof NetworkError) return t('errors.network');
  if (isAbortError(error)) return t('errors.cancelled');
  if (error instanceof Error && error.message) return error.message;
  return t('errors.unknown');
}

export function isNotFound(error: unknown): boolean {
  return error instanceof ApiError && error.status === 404;
}
