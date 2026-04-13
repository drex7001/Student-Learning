import { DiagnosisWorkspace } from "@/components/diagnosis-workspace";

export default async function DiagnosisPage({
  searchParams,
}: {
  searchParams: Promise<{ student?: string; concept?: string }>;
}) {
  const params = await searchParams;
  const studentId = params.student ?? "STU-001";
  const conceptId = params.concept ?? "ALG-024";

  return (
    <main className="flex w-full flex-1 flex-col px-4 py-5 md:px-6 xl:px-8">
      <div className="mb-5 max-w-4xl">
        <p className="font-mono text-xs uppercase tracking-[0.28em] text-teal">Student Diagnosis</p>
        <h1 className="mt-4 text-4xl font-semibold tracking-tight text-foreground md:text-5xl">
          One learner. One concept. One decision surface.
        </h1>
        <p className="mt-4 text-base leading-8 text-muted">
          This route is only for targeted diagnosis. Queue management and concept graph exploration
          live in their own routes.
        </p>
      </div>

      <DiagnosisWorkspace initialStudentId={studentId} initialConceptId={conceptId} />
    </main>
  );
}
