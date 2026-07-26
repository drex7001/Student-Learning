"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "./api";

type State<T> = { data: T | null; error: string | null; loading: boolean };

/**
 * Fetch-on-mount with abort handling.
 *
 * The previous components raced: rapid filter changes could let a slow earlier
 * response overwrite a newer one. Each run aborts the last, so the newest request
 * always wins.
 */
export function useApi<T>(path: string | null, deps: unknown[] = []) {
  const [state, setState] = useState<State<T>>({ data: null, error: null, loading: Boolean(path) });
  const controller = useRef<AbortController | null>(null);
  const [nonce, setNonce] = useState(0);

  const refresh = useCallback(() => setNonce((value) => value + 1), []);

  useEffect(() => {
    if (!path) {
      setState({ data: null, error: null, loading: false });
      return;
    }
    controller.current?.abort();
    const next = new AbortController();
    controller.current = next;

    setState((current) => ({ ...current, loading: true, error: null }));
    api
      .get<T>(path, next.signal)
      .then((data) => {
        if (!next.signal.aborted) setState({ data, error: null, loading: false });
      })
      .catch((caught: unknown) => {
        if (next.signal.aborted) return;
        setState({
          data: null,
          error: caught instanceof Error ? caught.message : "Request failed.",
          loading: false,
        });
      });

    return () => next.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, nonce, ...deps]);

  return { ...state, refresh };
}
