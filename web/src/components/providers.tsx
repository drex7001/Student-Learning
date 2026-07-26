"use client";

import { createContext, useCallback, useContext, useMemo, useSyncExternalStore } from "react";

import { I18nProvider } from "@/lib/i18n";
import { createPersistentStore } from "@/lib/persistent-store";

type Theme = "light" | "dark";

const isTheme = (value: string): value is Theme => value === "light" || value === "dark";

/**
 * The `<html class="dark">` stamp is applied by the inline script in the document
 * head before first paint, so there is no flash. This store keeps React in step with
 * it and persists the choice.
 */
const themeStore = createPersistentStore<Theme>({
  key: "wellbeing.theme",
  fallback: "light",
  isValid: isTheme,
  onChange: (value) => {
    document.documentElement.classList.toggle("dark", value === "dark");
  },
});

const ThemeContext = createContext<{ theme: Theme; toggle: () => void } | null>(null);

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) throw new Error("useTheme must be used inside Providers");
  return context;
}

export function Providers({ children }: { children: React.ReactNode }) {
  const theme = useSyncExternalStore(
    themeStore.subscribe,
    themeStore.getSnapshot,
    themeStore.getServerSnapshot,
  );

  const toggle = useCallback(() => {
    themeStore.set(themeStore.getSnapshot() === "dark" ? "light" : "dark");
  }, []);

  const value = useMemo(() => ({ theme, toggle }), [theme, toggle]);

  return (
    <ThemeContext.Provider value={value}>
      <I18nProvider>{children}</I18nProvider>
    </ThemeContext.Provider>
  );
}

/**
 * Runs before hydration so the correct surfaces paint immediately. Kept minimal and
 * failure-tolerant: a blocked localStorage must not stop the page rendering.
 */
export const themeBootstrapScript = `
try {
  var stored = localStorage.getItem('wellbeing.theme');
  var dark = stored ? stored === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches;
  if (dark) document.documentElement.classList.add('dark');
  var locale = localStorage.getItem('wellbeing.locale');
  if (locale === 'si' || locale === 'en') document.documentElement.lang = locale;
} catch (e) {}
`;
