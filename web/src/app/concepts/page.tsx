import { ConceptExplorer } from "@/components/concept-explorer";

export default async function ConceptsPage({
  searchParams,
}: {
  searchParams: Promise<{ concept?: string }>;
}) {
  const params = await searchParams;
  const conceptId = params.concept ?? "ALG-024";

  return (
    <main className="flex w-full flex-1 flex-col px-4 py-5 md:px-6 xl:px-8">
      <ConceptExplorer initialConceptId={conceptId} />
    </main>
  );
}
