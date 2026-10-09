import { useCallback, useMemo } from 'react';
import { useSearchParams } from 'react-router';
import { useUiStore } from '@/store/uiStore';
import { parseTreeAgeParams, toSearchParams, withCountry } from './logic/treeAgeLogic';
import type { TreeAgeInputs } from './types';

/**
 * The address bar is the page's memory: reading gives the inputs, writing replaces the current
 * address (no new history entry per slider step), so a copied link always reproduces the page.
 */
export function useTreeAgeUrl() {
  const [params, setParams] = useSearchParams();
  const storeCountry = useUiStore((s) => s.country);

  const wanted = useMemo(
    () => parseTreeAgeParams(params, { country: storeCountry }),
    [params, storeCountry],
  );

  /**
   * Applies a change. `shown` is what the page is showing now, so that a default the person has
   * seen (the first species in the list) becomes part of the address as soon as they change
   * anything.
   */
  const commit = useCallback(
    (patch: Partial<TreeAgeInputs>, shown: TreeAgeInputs) => {
      setParams(
        (previous) => {
          const current = parseTreeAgeParams(previous, { country: storeCountry });
          const { country, ...rest } = patch;
          let next: TreeAgeInputs = {
            ...current,
            speciesId: shown.speciesId ?? current.speciesId,
            subdivision: shown.subdivision,
          };
          if (country !== undefined) next = withCountry(next, country);
          return toSearchParams({ ...next, ...rest }, previous);
        },
        { replace: true },
      );
    },
    [setParams, storeCountry],
  );

  return { wanted, commit };
}
