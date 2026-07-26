"use client";

import { GraduationCap, ShieldCheck } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { ErrorNote, Field, controlClass, primaryButtonClass } from "@/components/ui";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { useApi } from "@/lib/use-api";
import type { CurrentUser } from "@/lib/types";

const DEMO_PASSWORD = "wellbeing2026";

type DemoAccount = {
  role: string;
  username: string;
  display_name: string;
  role_title: string | null;
  school_name: string | null;
};

function LoginForm() {
  const { t } = useI18n();
  const router = useRouter();
  const params = useSearchParams();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  // Read from the API rather than hardcoded: seeded names shift whenever the
  // generator changes, and a stale example is worse than none.
  const { data: demoAccounts } = useApi<DemoAccount[]>("/api/auth/demo-accounts");

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      const user = await api.post<CurrentUser>("/api/auth/login", { username, password });
      const next = params.get("next");
      // Only follow an internal path, so `?next=` cannot bounce anyone off-site.
      const destination = next && next.startsWith("/") && !next.startsWith("//") ? next : user.home_path;
      router.push(destination);
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : t("common.error"));
      setPending(false);
    }
  }

  function applyDemoAccount(account: string) {
    setUsername(account);
    setPassword(DEMO_PASSWORD);
  }

  return (
    <div className="grid min-h-svh place-items-center px-4 py-10">
      <div className="w-full max-w-[880px]">
        <div className="grid gap-6 md:grid-cols-[1.05fr_0.95fr]">
          <div className="flex flex-col justify-center">
            <span
              aria-hidden
              className="mb-4 grid size-10 place-items-center rounded-card bg-indigo text-[15px] font-semibold text-white"
            >
              ස
            </span>
            <h1 className="text-[28px] font-semibold leading-tight tracking-tight">
              {t("app.name")}
            </h1>
            <p className="mt-2 max-w-prose text-[14px] text-ink-secondary">{t("auth.subtitle")}</p>
            <p className="mt-5 max-w-prose border-l-2 border-rule pl-3 text-[12.5px] text-ink-muted">
              {t("app.demoBanner")}
            </p>
          </div>

          <div className="rounded-card border border-rule bg-surface p-5">
            <h2 className="text-[15px] font-semibold">{t("auth.title")}</h2>

            <form onSubmit={submit} className="mt-4 grid gap-3.5">
              <Field label={t("auth.username")}>
                <input
                  className={controlClass}
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                  autoComplete="username"
                  required
                />
              </Field>
              <Field label={t("auth.password")}>
                <input
                  type="password"
                  className={controlClass}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  autoComplete="current-password"
                  required
                />
              </Field>

              {error ? <ErrorNote message={error} /> : null}

              <button type="submit" className={primaryButtonClass} disabled={pending}>
                {pending ? t("auth.signingIn") : t("auth.submit")}
              </button>
            </form>

            {demoAccounts && demoAccounts.length > 0 ? (
              <div className="mt-5 border-t border-rule pt-4">
                <p className="text-[10.5px] font-medium uppercase tracking-[0.14em] text-ink-muted">
                  {t("auth.demoAccounts")}
                </p>
                <ul className="mt-2 grid gap-1">
                  {demoAccounts.map((account) => {
                    const Icon = account.role === "student" ? GraduationCap : ShieldCheck;
                    return (
                      <li key={account.username}>
                        <button
                          type="button"
                          onClick={() => applyDemoAccount(account.username)}
                          className="grid w-full grid-cols-[auto_minmax(0,1fr)] items-center gap-x-2 gap-y-0.5 rounded-chip px-2 py-1.5 text-left text-[12.5px] transition-colors hover:bg-sunken"
                        >
                          <Icon className="size-3.5 shrink-0 text-ink-muted" aria-hidden />
                          <span className="truncate text-ink-secondary">
                            {account.role_title ?? account.role}
                          </span>
                          <span aria-hidden />
                          <span className="num truncate text-ink">{account.username}</span>
                        </button>
                      </li>
                    );
                  })}
                </ul>
                <p className="mt-2 text-[11.5px] text-ink-muted">
                  Password for all demonstration accounts:{" "}
                  <span className="num">{DEMO_PASSWORD}</span>
                </p>
              </div>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginForm />
    </Suspense>
  );
}
