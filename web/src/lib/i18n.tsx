"use client";

/**
 * English / Sinhala UI strings.
 *
 * Structured so Tamil is a data-only addition: add `ta.ts` with the same keys and a
 * third entry in `DICTIONARIES`. Content that must be verified by a speaker — subject
 * names, concept descriptions, quiz banks, risk-factor copy — is served from the
 * database with `_si` fields rather than being duplicated here.
 */

import { createContext, useCallback, useContext, useMemo, useSyncExternalStore } from "react";

import { createPersistentStore } from "./persistent-store";

import type { Locale } from "./types";

const en = {
  "app.name": "Student Wellbeing Monitoring",
  "app.demoBanner":
    "Demonstration data. Fictional schools and students; risk figures come from illustrative expert-elicited priors, not validated Sri Lankan estimates.",

  "nav.overview": "Overview",
  "nav.caseload": "Caseload",
  "nav.classes": "Classes",
  "nav.concepts": "Concept map",
  "nav.queue": "Support queue",
  "nav.alerts": "Alerts",
  "nav.myProgress": "My progress",
  "nav.myLessons": "Lessons",
  "nav.quiz": "Practice quiz",
  "nav.signOut": "Sign out",

  "auth.title": "Sign in",
  "auth.subtitle": "Wellbeing monitoring for Sri Lankan schools",
  "auth.username": "Username",
  "auth.password": "Password",
  "auth.submit": "Sign in",
  "auth.signingIn": "Signing in…",
  "auth.demoAccounts": "Demonstration accounts",
  "auth.teacherPortal": "Teacher and counsellor portal",
  "auth.studentPortal": "Student portal",

  "band.needs_attention": "Needs attention now",
  "band.watch": "Watch",
  "band.not_marked": "Nothing marked",

  "status.support_now": "Support now",
  "status.watch": "Watch",
  "status.ready": "Ready",
  "status.missing_evidence": "No evidence yet",

  "risk.title": "Disengagement screen",
  "risk.pHigh": "Share who leave",
  "risk.basis": "How this number is arrived at",
  "risk.drivers": "What's behind it",
  "risk.driversNote":
    "Association, not the effect of acting. Each row compares this student's recorded circumstance against its reference state.",
  "risk.actions": "What would help",
  "risk.actionsNote":
    "Estimated by intervening on the model, not by conditioning on it. Select several to see their joint effect.",
  "risk.asking": "What to find out next",
  "risk.askingNote": "Unrecorded circumstances, ranked by how far the answer could move the figure.",
  "risk.routes": "How it reaches the outcome",
  "risk.locked": "Not a lever",
  "risk.lockedNote":
    "These cannot be intervened on. Asking what would change if a child were different is a forbidden question, not a malformed one.",
  "risk.evidence": "Record",
  "risk.notRecorded": "Not recorded",
  "risk.ahead": "Circumstances ahead",
  "risk.aheadNote":
    "Circumstances point higher than the attendance register currently shows.",
  "risk.plan": "Support plan",
  "risk.jointEffect": "Joint effect",
  "risk.sumOfParts": "Sum of the separate effects",
  "risk.offerSupport": "Open an offer of support",
  "risk.screening": "The whole screen, in twelve numbers",

  "caseload.title": "Caseload",
  "caseload.threshold": "Review threshold",
  "caseload.flagged": "flagged for review",
  "caseload.sortRisk": "Risk",
  "caseload.sortGap": "Gap",
  "caseload.sortName": "Name",
  "caseload.search": "Search by name or class",
  "caseload.empty": "No learners match this filter.",

  "shared.title": "Shared conditions",
  "shared.note":
    "A concern this many learners share is a condition of the school, not a property of the students who carry it.",
  "shared.schoolLevel": "School-level fix",

  "peers.title": "Peer connections",
  "peers.ties": "connections",
  "peers.fewTies": "few connections",

  "learn.progress": "Your progress",
  "learn.strong": "Going well",
  "learn.practise": "Worth practising",
  "learn.startQuiz": "Start practice quiz",
  "learn.submitQuiz": "Submit answers",
  "learn.yourScore": "Your score",
  "learn.tryAgain": "Try another quiz",
  "learn.noQuiz": "No practice questions available for these topics yet.",

  "common.loading": "Loading…",
  "common.error": "Something went wrong.",
  "common.retry": "Try again",
  "common.of": "of",
  "common.student": "Student",
  "common.class": "Class",
  "common.school": "School",
  "common.subject": "Subject",
  "common.save": "Save",
  "common.saved": "Saved",
  "common.cancel": "Cancel",
  "common.close": "Close",
  "common.viewRecord": "Open record",
  "common.language": "භාෂාව / Language",
  "common.theme": "Theme",
} as const;

export type MessageKey = keyof typeof en;

const si: Record<MessageKey, string> = {
  "app.name": "ශිෂ්‍ය සුවතා නිරීක්ෂණය",
  "app.demoBanner":
    "නිදර්ශන දත්ත. ප්‍රබන්ධ පාසල් සහ සිසුන්; අවදානම් අගයන් නිදර්ශන පූර්ව අනුමාන මත පදනම් වේ, තහවුරු කළ ශ්‍රී ලාංකික ඇස්තමේන්තු නොවේ.",

  "nav.overview": "දළ විශ්ලේෂණය",
  "nav.caseload": "සිසු ලැයිස්තුව",
  "nav.classes": "පන්ති",
  "nav.concepts": "සංකල්ප සිතියම",
  "nav.queue": "සහාය පෝලිම",
  "nav.alerts": "අනතුරු ඇඟවීම්",
  "nav.myProgress": "මගේ ප්‍රගතිය",
  "nav.myLessons": "පාඩම්",
  "nav.quiz": "අභ්‍යාස ප්‍රශ්න",
  "nav.signOut": "පිටවීම",

  "auth.title": "පිවිසෙන්න",
  "auth.subtitle": "ශ්‍රී ලංකා පාසල් සඳහා සුවතා නිරීක්ෂණය",
  "auth.username": "පරිශීලක නාමය",
  "auth.password": "මුරපදය",
  "auth.submit": "පිවිසෙන්න",
  "auth.signingIn": "පිවිසෙමින්…",
  "auth.demoAccounts": "නිදර්ශන ගිණුම්",
  "auth.teacherPortal": "ගුරු හා උපදේශක පිවිසුම",
  "auth.studentPortal": "ශිෂ්‍ය පිවිසුම",

  "band.needs_attention": "දැන් අවධානය අවශ්‍යයි",
  "band.watch": "නිරීක්ෂණය කරන්න",
  "band.not_marked": "සලකුණු කර නැත",

  "status.support_now": "දැන් සහාය",
  "status.watch": "නිරීක්ෂණය",
  "status.ready": "සූදානම්",
  "status.missing_evidence": "සාක්ෂි නොමැත",

  "risk.title": "පාසලෙන් ඉවත්වීමේ පරීක්ෂාව",
  "risk.pHigh": "ඉවත් වන ප්‍රතිශතය",
  "risk.basis": "මෙම අගය ලැබෙන ආකාරය",
  "risk.drivers": "මෙයට හේතු",
  "risk.driversNote":
    "ක්‍රියා කිරීමේ ප්‍රතිඵලය නොව සම්බන්ධතාවයකි. සෑම පේළියක්ම වාර්තා වූ තත්ත්වය එහි මූලික තත්ත්වය සමඟ සසඳයි.",
  "risk.actions": "උදව් වන දේ",
  "risk.actionsNote":
    "ආකෘතියට මැදිහත් වීමෙන් ගණනය කර ඇත. ඒකාබද්ධ බලපෑම බැලීමට කිහිපයක් තෝරන්න.",
  "risk.asking": "ඊළඟට දැනගත යුතු දේ",
  "risk.askingNote": "වාර්තා නොවූ තත්ත්ව, පිළිතුර අගය වෙනස් කළ හැකි ප්‍රමාණය අනුව.",
  "risk.routes": "ප්‍රතිඵලයට ළඟා වන ආකාරය",
  "risk.locked": "වෙනස් කළ නොහැකි",
  "risk.lockedNote":
    "මේවාට මැදිහත් විය නොහැක. දරුවෙකු වෙනස් නම් කුමක් වේද යන්න තහනම් ප්‍රශ්නයකි.",
  "risk.evidence": "වාර්තාව",
  "risk.notRecorded": "වාර්තා කර නැත",
  "risk.ahead": "තත්ත්ව ඉදිරියෙන්",
  "risk.aheadNote": "පැමිණීමේ ලේඛනයට වඩා තත්ත්ව ඉහළ අවදානමක් පෙන්වයි.",
  "risk.plan": "සහාය සැලැස්ම",
  "risk.jointEffect": "ඒකාබද්ධ බලපෑම",
  "risk.sumOfParts": "වෙන් වෙන් බලපෑම්වල එකතුව",
  "risk.offerSupport": "සහාය ලබා දීමක් ආරම්භ කරන්න",
  "risk.screening": "සම්පූර්ණ පරීක්ෂාව, අගයන් දොළහකින්",

  "caseload.title": "සිසු ලැයිස්තුව",
  "caseload.threshold": "සමාලෝචන සීමාව",
  "caseload.flagged": "සමාලෝචනය සඳහා",
  "caseload.sortRisk": "අවදානම",
  "caseload.sortGap": "පරතරය",
  "caseload.sortName": "නම",
  "caseload.search": "නම හෝ පන්තිය අනුව සොයන්න",
  "caseload.empty": "මෙම පෙරහනට ගැලපෙන සිසුන් නැත.",

  "shared.title": "පොදු තත්ත්ව",
  "shared.note":
    "මෙතරම් සිසුන් ගණනක් බෙදාගන්නා තත්ත්වයක් යනු පාසලේ තත්ත්වයකි, එය දරන සිසුන්ගේ ගුණාංගයක් නොවේ.",
  "shared.schoolLevel": "පාසල් මට්ටමේ විසඳුම",

  "peers.title": "සම වයස් සම්බන්ධතා",
  "peers.ties": "සම්බන්ධතා",
  "peers.fewTies": "සම්බන්ධතා අඩුයි",

  "learn.progress": "ඔබේ ප්‍රගතිය",
  "learn.strong": "හොඳින් යයි",
  "learn.practise": "අභ්‍යාස කළ යුතුයි",
  "learn.startQuiz": "අභ්‍යාස ප්‍රශ්න ආරම්භ කරන්න",
  "learn.submitQuiz": "පිළිතුරු යවන්න",
  "learn.yourScore": "ඔබේ ලකුණු",
  "learn.tryAgain": "තවත් ප්‍රශ්න මාලාවක්",
  "learn.noQuiz": "මෙම මාතෘකා සඳහා තවම අභ්‍යාස ප්‍රශ්න නොමැත.",

  "common.loading": "පූරණය වෙමින්…",
  "common.error": "යම් දෝෂයක් ඇති විය.",
  "common.retry": "නැවත උත්සාහ කරන්න",
  "common.of": "න්",
  "common.student": "සිසුවා",
  "common.class": "පන්තිය",
  "common.school": "පාසල",
  "common.subject": "විෂය",
  "common.save": "සුරකින්න",
  "common.saved": "සුරකින ලදී",
  "common.cancel": "අවලංගු",
  "common.close": "වසන්න",
  "common.viewRecord": "වාර්තාව විවෘත කරන්න",
  "common.language": "භාෂාව / Language",
  "common.theme": "තේමාව",
};

const DICTIONARIES: Record<Locale, Record<MessageKey, string>> = { en, si };

type I18nValue = {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: MessageKey) => string;
  /** Pick the Sinhala variant of a database field when the locale is `si`. */
  pick: (english: string | null | undefined, sinhala: string | null | undefined) => string;
};

const I18nContext = createContext<I18nValue | null>(null);

const isLocale = (value: string): value is Locale => value === "en" || value === "si";

const localeStore = createPersistentStore<Locale>({
  key: "wellbeing.locale",
  fallback: "en",
  isValid: isLocale,
  onChange: (value) => {
    document.documentElement.lang = value;
  },
});

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const locale = useSyncExternalStore(
    localeStore.subscribe,
    localeStore.getSnapshot,
    localeStore.getServerSnapshot,
  );

  const setLocale = useCallback((next: Locale) => localeStore.set(next), []);

  const value = useMemo<I18nValue>(
    () => ({
      locale,
      setLocale,
      t: (key) => DICTIONARIES[locale][key] ?? DICTIONARIES.en[key] ?? key,
      pick: (english, sinhala) => (locale === "si" && sinhala ? sinhala : english ?? ""),
    }),
    [locale, setLocale],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  const context = useContext(I18nContext);
  if (!context) throw new Error("useI18n must be used inside I18nProvider");
  return context;
}
