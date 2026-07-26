"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { AppShell, type NavItem } from "@/components/app-shell";
import { Loading } from "@/components/ui";
import { useI18n } from "@/lib/i18n";
import { useApi } from "@/lib/use-api";
import type { CurrentUser } from "@/lib/types";

const NAV: NavItem[] = [
  { href: "/teacher", labelKey: "nav.overview" },
  { href: "/teacher/caseload", labelKey: "nav.caseload" },
  { href: "/teacher/classes", labelKey: "nav.classes" },
  { href: "/teacher/queue", labelKey: "nav.queue" },
  { href: "/teacher/concepts", labelKey: "nav.concepts" },
];

export default function TeacherLayout({ children }: { children: React.ReactNode }) {
  const { t } = useI18n();
  const router = useRouter();
  const { data: user, loading } = useApi<CurrentUser>("/api/auth/me");

  useEffect(() => {
    // A student who reaches a teacher URL is sent to their own portal. The API
    // refuses the data regardless; this only avoids showing them an error page.
    if (user && user.role === "student") router.replace("/student");
  }, [user, router]);

  if (loading || !user) return <Loading label={t("common.loading")} />;
  if (user.role === "student") return null;

  return (
    <AppShell user={user} nav={NAV}>
      {children}
    </AppShell>
  );
}
