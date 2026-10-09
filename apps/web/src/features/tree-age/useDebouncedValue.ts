import { useEffect, useState } from 'react';

/**
 * The value once it has stopped changing for `delayMs` (a slider being dragged settles before it
 * is used). While nothing has settled yet, because the value is still null or undefined, the
 * first real value is taken on the next tick instead of waiting, so a page never sits idle on
 * load, and the very first drag is already debounced.
 */
export function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [settled, setSettled] = useState(value);
  useEffect(() => {
    if (Object.is(value, settled)) return undefined;
    const timer = setTimeout(() => setSettled(value), settled == null ? 0 : delayMs);
    return () => clearTimeout(timer);
  }, [value, settled, delayMs]);
  return settled;
}
