import { NextRequest, NextResponse } from "next/server";

// Route protection here is a UX hint only, not the security boundary. The actual refresh
// token is an HttpOnly cookie set by the API's own origin (Railway) — cross-origin from
// this frontend (Vercel), so this middleware can never see it. "has_session" is a separate,
// non-sensitive cookie this app sets on itself after login (see lib/sessionHint.ts) purely
// to decide whether to redirect before render. Real authorization happens API-side via JWT
// on every request; a stale or forged hint cookie just gets a 401 from the API, not access.
const PROTECTED_PREFIXES = ["/orders", "/vendor", "/cart", "/checkout", "/account"];

export function proxy(request: NextRequest) {
  const isProtected = PROTECTED_PREFIXES.some((prefix) =>
    request.nextUrl.pathname.startsWith(prefix)
  );
  if (!isProtected) return NextResponse.next();

  const hasSession = request.cookies.has("has_session");
  if (!hasSession) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("next", request.nextUrl.pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/orders",
    "/orders/:path*",
    "/vendor/:path*",
    "/cart",
    "/cart/:path*",
    "/checkout/:path*",
    "/account",
  ],
};
