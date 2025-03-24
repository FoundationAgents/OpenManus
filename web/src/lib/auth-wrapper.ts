import { cookies } from 'next/headers';
import { verifyToken } from './auth';

export interface AuthUser {
  id: string;
  email: string;
  name?: string;
  isSystemUser: boolean;
  isFirstLogin: boolean;
  organizationId: string;
}

export interface AuthResult<T> {
  data?: T;
  error?: string;
}

/**
 * Authentication wrapper type
 */
type AuthWrapper<T> = (fn: (user: AuthUser, ...args: any[]) => Promise<T>) => (...args: any[]) => Promise<AuthResult<T>>;

/**
 * System user authentication wrapper
 */
export const withSystemUserAuth: AuthWrapper<any> = fn => {
  return async (...args) => {
    try {
      const cookieStore = await cookies();
      const token = cookieStore.get('token')?.value;

      if (!token) {
        return { error: 'Unauthorized access' };
      }

      const user = await verifyToken(token);
      if (!user.isSystemUser) {
        return { error: 'Only system users can perform this action' };
      }

      const result = await fn(user, ...args);
      return { data: result };
    } catch (error) {
      console.error('Authentication error:', error);
      return { error: 'Authentication failed' };
    }
  };
};

/**
 * Regular user authentication wrapper
 */
export const withUserAuth: AuthWrapper<any> = fn => {
  return async (...args) => {
    try {
      const cookieStore = await cookies();
      const token = cookieStore.get('token')?.value;

      if (!token) {
        return { error: 'Unauthorized access' };
      }

      const user = await verifyToken(token);
      const result = await fn(user, ...args);
      return { data: result };
    } catch (error) {
      console.error('Authentication error:', error);
      return { error: 'Authentication failed' };
    }
  };
};
