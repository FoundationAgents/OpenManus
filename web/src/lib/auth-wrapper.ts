import { cookies } from 'next/headers';
import { AuthUser, verifyToken } from './auth';
import { prisma } from './prisma';
import { Organizations } from '@prisma/client';

interface AuthResult<T> {
  data?: T;
  error?: string;
}

/**
 * Authentication wrapper type
 */
export type AuthWrapper<T, R> = (
  fn: (ctx: { user: AuthUser; organization: Organizations; args: R }) => Promise<T>
) => (args: R) => Promise<AuthResult<T>>;

/**
 * Regular user authentication wrapper
 */
export function withUserAuth<R, T = any>(fn: (ctx: { user: AuthUser; organization: Organizations; args: R }) => Promise<T>) {
  return async (args: R) => {
    try {
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

      const result = await fn({ user, organization, args });
      return { data: result };
    } catch (error) {
      console.error('Authentication error:', error);
      throw new Error('Authentication failed');
    }
  };
}
