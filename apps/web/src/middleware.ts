import { NextRequest, NextResponse } from "next/server";

// Routes that we want to treat carefully on the server side
const PROTECTED_PATHS = ["/dashboard", "/pets", "/analyze", "/diet-plans", "/reports", "/admin"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Add no-cache headers for protected routes so the browser always re-validates
  const isProtected = PROTECTED_PATHS.some((p) => pathname.startsWith(p));
  if (isProtected) {
    // For admin routes we also perform a server-side check for an auth cookie.
    if (pathname.startsWith("/admin")) {
      try {
        const raw = request.cookies.get("dietpaw_user")?.value;
        if (!raw) {
          // Not signed in, redirect to sign-in
          return NextResponse.redirect(new URL("/sign-in", request.url));
        }
        const user = JSON.parse(decodeURIComponent(raw));
        if (!user || user.is_admin !== true) {
          // Signed in but not an admin
          return NextResponse.redirect(new URL("/analyze", request.url));
        }
      } catch (e) {
        return NextResponse.redirect(new URL("/sign-in", request.url));
      }
    }

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
