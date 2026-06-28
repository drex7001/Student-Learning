import { StudentHelpDashboard } from "@/components/student-help-dashboard";

export default async function SupportPage({
  searchParams,
}: {
  searchParams: Promise<{ subject?: string }>;
}) {
  const params = await searchParams;

  return (
    <main className="flex w-full flex-1 flex-col px-4 py-5 md:px-6 xl:px-8">
      <StudentHelpDashboard initialSubjectId={params.subject ?? "OL-MATH"} />
    </main>
  );
}
