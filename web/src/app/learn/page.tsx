import { LearningPortal } from "@/components/learning-portal";

export default async function LearnPage({
  searchParams,
}: {
  searchParams: Promise<{ subject?: string; student?: string }>;
}) {
  const params = await searchParams;

  return (
    <LearningPortal
      initialSubjectId={params.subject ?? "OL-MATH"}
      initialStudentId={params.student ?? "STU-001"}
    />
  );
}
