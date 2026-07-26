import { cookies } from "next/headers";
import { redirect } from "next/navigation";

/**
 * There is no public landing page: the two portals are different products for
 * different audiences, so the root routes to whichever one applies.
 */
export default async function RootPage() {
  const store = await cookies();
  if (!store.get("wellbeing_session")) {
    redirect("/login");
  }
  redirect("/teacher");
}
