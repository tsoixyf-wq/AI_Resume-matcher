"use client";

import { useState, useEffect, useCallback, useRef } from "react";

interface UseApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

interface UseApiReturn<T> extends UseApiState<T> {
  refresh: () => void;
  setData: (data: T | null) => void;
}

/**
 * Generic data-fetching hook with loading/error/refresh.
 * Replaces the manual useState+useEffect+try/catch pattern.
 */
export function useApi<T>(
  fetcher: () => Promise<T>,
  options?: {
    autoFetch?: boolean;
    onError?: (err: unknown) => void;
  },
): UseApiReturn<T> {
  const { autoFetch = true, onError } = options || {};
  const [state, setState] = useState<UseApiState<T>>({
    data: null,
    loading: autoFetch,
    error: null,
  });

  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const fetch = useCallback(async () => {
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const result = await fetcherRef.current();
      setState({ data: result, loading: false, error: null });
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "请求失败，请稍后重试";
      setState((s) => ({ ...s, loading: false, error: msg }));
      onError?.(err);
    }
  }, [onError]);

  useEffect(() => {
    if (autoFetch) {
      fetch();
    }
  }, [autoFetch, fetch]);

  return {
    ...state,
    refresh: fetch,
    setData: (data: T | null) => setState((s) => ({ ...s, data })),
  };
}

export default useApi;
