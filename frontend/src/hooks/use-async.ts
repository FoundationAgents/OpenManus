import type { DependencyList } from 'react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { create } from 'zustand';
import { isEqual } from 'lodash';

type CacheStore = {
  caches: Map<boolean | string | symbol, any>;
  getCache: <R>(cacheKey: boolean | string | symbol) => R | undefined;
  setCache: <R>(cacheKey: boolean | string | symbol, data: R) => void;
};

const useCacheStore = create<CacheStore>((set, get) => ({
  caches: new Map(),
  getCache: cacheKey => {
    const { caches } = get();
    return caches.get(cacheKey) || undefined;
  },
  setCache: (cacheKey, data) => {
    set(state => {
      const newCaches = new Map(state.caches);
      newCaches.set(cacheKey, data);
      return { caches: newCaches };
    });
  },
}));

export const useAsync = <R, T extends unknown[]>(
  fn: (...params: T) => Promise<R>,
  params: T,
  options: { manual?: boolean; deps?: DependencyList; skip?: (params: T) => boolean; cache?: string | symbol } = {},
) => {
  const [data, setData] = useState<R | undefined>(undefined);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | undefined>(undefined);
  const fnRef = useRef(fn);
  const paramsRef = useRef(params);
  const { getCache, setCache } = useCacheStore();

  const cacheKey = options.cache || false;

  useEffect(() => {
    if (cacheKey && !options.manual) {
      const cachedData = getCache<R>(cacheKey);
      if (cachedData !== undefined) {
        setData(cachedData);
      }
    }
  }, [cacheKey, options.manual]);

  // Update function reference without triggering re-renders
  useEffect(() => {
    fnRef.current = fn;
  }, [fn]);

  // Deep compare params to prevent unnecessary re-renders
  useEffect(() => {
    if (!isEqual(paramsRef.current, params)) {
      paramsRef.current = params;
    }
  }, [params]);

  const shouldSkip = options.skip ? options.skip(params) : false;
  const run = useCallback(
    async (...runParams: T) => {
      if (shouldSkip) {
        return;
      }

      setIsLoading(true);
      try {
        const result = await fnRef.current(...runParams);
        setData(result);

        if (cacheKey) {
          setCache<R>(cacheKey, result);
        }

        return result;
      } catch (err) {
        setError(err as Error);
        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    [shouldSkip, cacheKey, ...(options.deps ?? [])],
  );

  const refresh = useCallback(() => {
    return run(...paramsRef.current);
  }, [run]);

  const mutate = useCallback(
    (dataAction: R | undefined | ((prev: R | undefined) => R)) => {
      const newData = typeof dataAction === 'function' ? (dataAction as (prev: R | undefined) => R)(data) : dataAction;
      setData(newData);
      setError(undefined);

      if (cacheKey && newData !== undefined) {
        setCache<R>(cacheKey, newData);
      }

      return newData;
    },
    [data, cacheKey],
  );

  useEffect(() => {
    if (options.manual) {
      return;
    }

    if (cacheKey) {
      const cachedData = getCache<R>(cacheKey);
      if (cachedData !== undefined) {
        setData(cachedData);
        return;
      }
    }
    run(...paramsRef.current);
  }, [run, options.manual, cacheKey]);

  return { data, isLoading, error, run, refresh, mutate };
};
