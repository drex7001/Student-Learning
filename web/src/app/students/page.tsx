import { SupportQueue } from "@/components/support-queue";

export default async function StudentsPage({
  searchParams,
}: {
  searchParams: Promise<{ subject?: string; concept?: string }>;
}) {
  const params = await searchParams;

  return (
    <main className="flex w-full flex-1 flex-col px-4 py-5 md:px-6 xl:px-8">
      <SupportQueue initialSubjectId={params.subject ?? "OL-MATH"} initialConceptId={params.concept} />
    </main>
  );
}
