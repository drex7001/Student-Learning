/**
 * A tiny external store backed by localStorage.
 *
 * Theme and locale live outside React, so they are read with `useSyncExternalStore`
 * rather than copied into state inside an effect. That avoids the cascading render
 * React 19 warns about, and means every subscriber updates together.
 */

export type PersistentStore<T extends string> = {
  subscribe: (listener: () => void) => () => void;
  getSnapshot: () => T;
  getServerSnapshot: () => T;
  set: (value: T) => void;
};

export function createPersistentStore<T extends string>({
  key,
  fallback,
  isValid,
  onChange,
}: {
  key: string;
  fallback: T;
  isValid: (value: string) => value is T;
  onChange?: (value: T) => void;
}): PersistentStore<T> {
  const listeners = new Set<() => void>();
  let cached: T | null = null;

  function read(): T {
    if (cached !== null) return cached;
    if (typeof window === "undefined") return fallback;
    const raw = window.localStorage.getItem(key);
    cached = raw && isValid(raw) ? raw : fallback;
    return cached;
  }

  return {
    subscribe(listener) {
      listeners.add(listener);
      return () => {
        listeners.delete(listener);
      };
    },
    getSnapshot: read,
    getServerSnapshot: () => fallback,
    set(value) {
      cached = value;
      window.localStorage.setItem(key, value);
      onChange?.(value);
      listeners.forEach((listener) => listener());
    },
  };
}
