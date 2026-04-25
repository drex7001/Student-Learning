import { ConceptExplorer } from "@/components/concept-explorer";

export default async function ConceptsPage({
  searchParams,
}: {
  searchParams: Promise<{ subject?: string; concept?: string }>;
}) {
  const params = await searchParams;
  const subjectId = params.subject ?? "OL-MATH";

  return (
    <main className="flex w-full flex-1 flex-col px-4 py-5 md:px-6 xl:px-8">
      <ConceptExplorer initialSubjectId={subjectId} initialConceptId={params.concept} />
    </main>
  );
}
