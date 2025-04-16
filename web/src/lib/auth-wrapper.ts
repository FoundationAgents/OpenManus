import { Organizations } from '@prisma/client';
import { cookies } from 'next/headers';
import { AuthUser, verifyToken } from './auth';
import { prisma } from './prisma';
import { to } from './to';

export type AuthWrapperContext<T> = { user: AuthUser; organization: Organizations; args: T };

export type AuthWrapped<T, R> = (ctx: AuthWrapperContext<T>) => Promise<R>;

export type AuthAction<T, R> = (args: T) => Promise<{ data: R; error: undefined } | { data: undefined; error: string }>;

/**
 * Authentication wrapper type
 */
export type AuthWrapper<T, R> = (fn: AuthWrapped<T, R>) => AuthAction<T, R>;

/**
 * Regular user authentication wrapper
 */
export function withUserAuth<T = unknown, R = unknown>(fn: AuthWrapped<T, R>): AuthAction<T, R> {
  return async (args: T) => {
    try {
    } catch (error) {
      console.error('Authentication error:', error);
      throw new Error('Authentication failed');
    }

    const [error, result] = await to(
      (async () => {
        const cookieStore = await cookies();
        const token = cookieStore.get('token')?.value;

        if (!token) {
          throw new Error('Unauthorized access');
        }

        const user = await verifyToken(token);
        const organizationUser = await prisma.organizationUsers.findMany({
          where: { userId: user.id },
        });

        if (organizationUser.length === 0) {
          throw new Error('User is not associated with any organization');
        }

        if (organizationUser.length > 1) {
          throw new Error('User is associated with multiple organizations');
        }

        const organization = await prisma.organizations.findUnique({
          where: { id: organizationUser[0].organizationId },
        });

        if (!organization) {
          throw new Error('Organization not found');
        }

        return { user, organization };
      })()
    );

    if (error) {
      throw new Error('Authentication failed: ' + error.message);
    }

    const res = await fn({ user: result.user, organization: result.organization, args });
    return { data: res, error: undefined };
  };
}
