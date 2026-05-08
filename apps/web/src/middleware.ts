import { NextRequest, NextResponse } from "next/server";

// Routes that require authentication (client-side check via AuthGuard)
// Middleware here only prevents caching of protected pages — actual auth
// is enforced by the AuthGuard component in the dashboard layout.
const PROTECTED_PATHS = ["/dashboard", "/pets", "/analyze", "/diet-plans", "/reports", "/admin"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Add no-cache headers for protected routes so the browser always re-validates
  const isProtected = PROTECTED_PATHS.some((p) => pathname.startsWith(p));
  if (isProtected) {
    const response = NextResponse.next();
    response.headers.set("Cache-Control", "no-store");
    return response;
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
  ],
};
