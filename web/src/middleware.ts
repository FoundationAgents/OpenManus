import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { verifyToken } from '@/lib/auth';

// Add paths that don't require authentication
const publicPaths = ['/login', '/signup', '/api/auth', '/share', '/api/share'];

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Handle API routes
  if (pathname.startsWith('/api/')) {
    // Skip auth for public API routes
    if (publicPaths.some(path => pathname.startsWith(path))) {
      return NextResponse.next();
    }

    // Verify token from cookie for API routes
    const cookieToken = request.cookies.get('token');
    if (!cookieToken) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    try {
      await verifyToken(cookieToken.value);
      return NextResponse.next();
    } catch (error) {
      return NextResponse.json({ error: 'Invalid token' }, { status: 401 });
    }
  }

  // Handle page routes
  // Check if the path is public
  const isPublicPath = publicPaths.some(path => pathname.startsWith(path));

  // Get token from cookie for page routes
  const cookieToken = request.cookies.get('token');

  // Handle private paths
  if (!isPublicPath) {
    if (!cookieToken) {
      return NextResponse.redirect(new URL('/login', request.url));
    }

    try {
      await verifyToken(cookieToken.value);
      return NextResponse.next();
    } catch {
      // Invalid token, clear it and redirect to login
      const response = NextResponse.redirect(new URL('/login', request.url));
      response.cookies.delete('token');
      return response;
    }
  }

  // Handle login page access
  if (pathname === '/login' && cookieToken) {
    try {
      await verifyToken(cookieToken.value);
      return NextResponse.redirect(new URL('/', request.url));
    } catch {
      // If token is invalid, delete it and stay on login page
      const response = NextResponse.next();
      response.cookies.delete('token');
      return response;
    }
  }

  return NextResponse.next();
}

// Configure which routes use this middleware
export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    '/((?!_next/static|_next/image|favicon.ico).*)',
  ],
};
