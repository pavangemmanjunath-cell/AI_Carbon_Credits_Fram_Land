import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useDebouncedValue } from './useDebouncedValue';

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

describe('useDebouncedValue', () => {
  it('returns the first value at once', () => {
    const { result } = renderHook(() => useDebouncedValue('first', 400));
    expect(result.current).toBe('first');
  });

  it('waits for the value to stop changing before using it', () => {
    const { result, rerender } = renderHook(({ value }) => useDebouncedValue(value, 400), {
      initialProps: { value: 30 },
    });
    rerender({ value: 31 });
    act(() => vi.advanceTimersByTime(399));
    expect(result.current).toBe(30);
    act(() => vi.advanceTimersByTime(1));
    expect(result.current).toBe(31);
  });

  it('starts counting again on every change, so a dragged slider settles once', () => {
    const seen: number[] = [];
    const { result, rerender } = renderHook(
      ({ value }) => {
        const settled = useDebouncedValue(value, 400);
        if (seen.at(-1) !== settled) seen.push(settled);
        return settled;
      },
      { initialProps: { value: 30 } },
    );
    for (const value of [31, 32, 33, 34, 35]) {
      rerender({ value });
      act(() => vi.advanceTimersByTime(200));
    }
    expect(result.current).toBe(30);
    act(() => vi.advanceTimersByTime(400));
    expect(result.current).toBe(35);
    expect(seen).toEqual([30, 35]);
  });

  it('drops a pending change when the value returns to the settled one', () => {
    const { result, rerender } = renderHook(({ value }) => useDebouncedValue(value, 400), {
      initialProps: { value: 'a' },
    });
    rerender({ value: 'b' });
    act(() => vi.advanceTimersByTime(300));
    rerender({ value: 'a' });
    act(() => vi.advanceTimersByTime(1000));
    expect(result.current).toBe('a');
  });

  it('takes the first real value on the next tick when nothing has settled yet', () => {
    const { result, rerender } = renderHook(
      ({ value }: { value: string | null }) => useDebouncedValue(value, 400),
      { initialProps: { value: null as string | null } },
    );
    expect(result.current).toBeNull();
    rerender({ value: '{"age":30}' });
    act(() => vi.advanceTimersByTime(0));
    expect(result.current).toBe('{"age":30}');
  });

  it('debounces the very next change, so the first drag after loading is not a flood', () => {
    const { result, rerender } = renderHook(
      ({ value }: { value: string | null }) => useDebouncedValue(value, 400),
      { initialProps: { value: null as string | null } },
    );
    rerender({ value: 'first' });
    act(() => vi.advanceTimersByTime(0));
    expect(result.current).toBe('first');
    for (const value of ['b', 'c', 'd']) {
      rerender({ value });
      act(() => vi.advanceTimersByTime(100));
    }
    expect(result.current).toBe('first');
    act(() => vi.advanceTimersByTime(300));
    expect(result.current).toBe('d');
  });

  it('lets a value go back to null after the delay, and takes the next real one at once', () => {
    const { result, rerender } = renderHook(
      ({ value }: { value: string | null }) => useDebouncedValue(value, 400),
      { initialProps: { value: 'a' as string | null } },
    );
    rerender({ value: null });
    act(() => vi.advanceTimersByTime(399));
    expect(result.current).toBe('a');
    act(() => vi.advanceTimersByTime(1));
    expect(result.current).toBeNull();
    rerender({ value: 'b' });
    act(() => vi.advanceTimersByTime(0));
    expect(result.current).toBe('b');
  });
});
