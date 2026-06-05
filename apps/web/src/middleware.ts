import { NextRequest, NextResponse } from "next/server";

// Routes that we want to treat carefully on the server side
const PROTECTED_PATHS = [
  "/dashboard",
  "/profile",
  "/pets",
  "/analyze",
  "/wellness",
  "/health-records",
  "/expenses",
  "/diet-plans",
  "/reports",
  "/admin",
];

const AUTH_PATHS = ["/login", "/signup", "/sign-in", "/sign-up"];

function isPathMatch(pathname: string, prefixes: string[]) {
  return prefixes.some((prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`));
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  const onProtectedRoute = isPathMatch(pathname, PROTECTED_PATHS);
  const onAuthRoute = isPathMatch(pathname, AUTH_PATHS);

  const rawUserCookie = request.cookies.get("dietpaw_user")?.value;
  let parsedUser: { is_admin?: boolean } | null = null;
  if (rawUserCookie) {
    try {
      parsedUser = JSON.parse(decodeURIComponent(rawUserCookie));
    } catch {
      parsedUser = null;
    }
  }

  // Add no-cache headers for protected routes so the browser always re-validates
  if (onProtectedRoute) {
    if (!parsedUser) {
      const nextUrl = new URL("/login", request.url);
      nextUrl.searchParams.set("next", pathname);
      return NextResponse.redirect(nextUrl);
    }

    if (pathname.startsWith("/admin") && parsedUser.is_admin !== true) {
      return NextResponse.redirect(new URL("/dashboard", request.url));
    }

    const response = NextResponse.next();
    response.headers.set("Cache-Control", "no-store");
    return response;
  }

  if (onAuthRoute && parsedUser) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
  ],
};
