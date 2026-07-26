import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const SESSION_COOKIE = "wellbeing_session";

/**
 * Optimistic route guard.
 *
 * This only checks that a session cookie is present, so an unauthenticated visitor
 * lands on the sign-in page instead of a flash of empty dashboard. It is deliberately
 * not the authorisation boundary — every rule that matters (which learner a student
 * may read, that no student reaches the risk endpoints) is enforced by the API
 * against a verified token.
 */
export function proxy(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  const hasSession = Boolean(request.cookies.get(SESSION_COOKIE)?.value);

  if (!hasSession) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    url.search = `?next=${encodeURIComponent(pathname + search)}`;
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/teacher/:path*", "/student/:path*"],
};
