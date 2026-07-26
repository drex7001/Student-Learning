"use client";

import { LogOut, Menu, Moon, Sun, X } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";

import { api } from "@/lib/api";
import { cn } from "@/lib/format";
import { useI18n, type MessageKey } from "@/lib/i18n";
import type { CurrentUser } from "@/lib/types";
import { useTheme } from "@/components/providers";

export type NavItem = { href: string; labelKey: MessageKey };

export function AppShell({
  user,
  nav,
  children,
}: {
  user: CurrentUser;
  nav: NavItem[];
  children: React.ReactNode;
}) {
  const { t, locale, setLocale, pick } = useI18n();
  const { theme, toggle } = useTheme();
  const pathname = usePathname();
  const router = useRouter();
  const [menuOpen, setMenuOpen] = useState(false);

  async function signOut() {
    await api.post("/api/auth/logout").catch(() => undefined);
    router.push("/login");
    router.refresh();
  }

  return (
    <div className="min-h-svh">
      {/* The provenance of every figure on every screen. Not dismissible. */}
      <p className="border-b border-rule bg-sunken px-4 py-1.5 text-center text-[11.5px] text-ink-secondary">
        {t("app.demoBanner")}
      </p>

      <header className="sticky top-0 z-40 border-b border-rule bg-surface/95 backdrop-blur">
        <div className="mx-auto flex max-w-[1400px] items-center gap-3 px-4 py-2.5">
          <Link href={user.home_path} className="flex min-w-0 items-center gap-2.5">
            <span aria-hidden className="grid size-7 shrink-0 place-items-center rounded-chip bg-indigo text-[12px] font-semibold text-white">
              ස
            </span>
            <span className="min-w-0">
              <span className="block truncate text-[13.5px] font-semibold leading-tight">
                {t("app.name")}
              </span>
              {user.school_name ? (
                <span className="block truncate text-[11.5px] leading-tight text-ink-muted">
                  {user.school_name}
                </span>
              ) : null}
            </span>
          </Link>

          <nav aria-label="Main" className="ml-4 hidden flex-1 items-center gap-0.5 lg:flex">
            {nav.map((item) => {
              const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "rounded-chip px-2.5 py-1.5 text-[13px] transition-colors",
                    active
                      ? "bg-indigo-soft font-medium text-indigo"
                      : "text-ink-secondary hover:text-ink",
                  )}
                >
                  {t(item.labelKey)}
                </Link>
              );
            })}
          </nav>

          <div className="ml-auto flex items-center gap-1.5">
            <div className="hidden items-center rounded-chip border border-rule sm:flex" role="group" aria-label={t("common.language")}>
              {(["en", "si"] as const).map((code) => (
                <button
                  key={code}
                  type="button"
                  onClick={() => setLocale(code)}
                  aria-pressed={locale === code}
                  className={cn(
                    "px-2 py-1 text-[12px] first:rounded-l-chip last:rounded-r-chip",
                    locale === code ? "bg-indigo-soft font-medium text-indigo" : "text-ink-muted",
                  )}
                >
                  {code === "en" ? "EN" : "සිං"}
                </button>
              ))}
            </div>

            <button
              type="button"
              onClick={toggle}
              className="rounded-chip border border-rule p-1.5 text-ink-secondary"
              aria-label={t("common.theme")}
            >
              {theme === "dark" ? <Moon className="size-4" aria-hidden /> : <Sun className="size-4" aria-hidden />}
            </button>

            <div className="hidden text-right md:block">
              <p className="text-[12.5px] font-medium leading-tight">
                {pick(user.display_name, user.display_name_si)}
              </p>
              <p className="text-[11px] leading-tight text-ink-muted">
                {user.role_title ?? user.role}
              </p>
            </div>

            <button
              type="button"
              onClick={signOut}
              className="rounded-chip border border-rule p-1.5 text-ink-secondary"
              aria-label={t("nav.signOut")}
            >
              <LogOut className="size-4" aria-hidden />
            </button>

            <button
              type="button"
              onClick={() => setMenuOpen((open) => !open)}
              className="rounded-chip border border-rule p-1.5 lg:hidden"
              aria-expanded={menuOpen}
              aria-label="Menu"
            >
              {menuOpen ? <X className="size-4" aria-hidden /> : <Menu className="size-4" aria-hidden />}
            </button>
          </div>
        </div>

        {menuOpen ? (
          <nav aria-label="Main" className="border-t border-rule px-4 py-2 lg:hidden">
            <ul className="grid gap-0.5">
              {nav.map((item) => (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    onClick={() => setMenuOpen(false)}
                    className="block rounded-chip px-2.5 py-2 text-[14px] text-ink-secondary"
                  >
                    {t(item.labelKey)}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
        ) : null}
      </header>

      <main className="mx-auto max-w-[1400px] px-4 py-5">{children}</main>
    </div>
  );
}
