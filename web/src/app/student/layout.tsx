"use client";

import { AppShell, type NavItem } from "@/components/app-shell";
import { Loading } from "@/components/ui";
import { useI18n } from "@/lib/i18n";
import { useApi } from "@/lib/use-api";
import type { CurrentUser } from "@/lib/types";

/**
 * The student portal is a learning product. It carries no risk score, no caseload and
 * no wellbeing flag — a flag must cost the student nothing if it was wrong, and being
 * told a model expects you to leave school is a cost. The API enforces this too.
 */
const NAV: NavItem[] = [
  { href: "/student", labelKey: "nav.myProgress" },
  { href: "/student/lessons", labelKey: "nav.myLessons" },
  { href: "/student/quiz", labelKey: "nav.quiz" },
];

export default function StudentLayout({ children }: { children: React.ReactNode }) {
  const { t } = useI18n();
  const { data: user, loading } = useApi<CurrentUser>("/api/auth/me");

  if (loading || !user) return <Loading label={t("common.loading")} />;

  return (
    <AppShell user={user} nav={NAV}>
      {children}
    </AppShell>
  );
}
