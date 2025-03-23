import { SignJWT, jwtVerify } from 'jose';

const JWT_SECRET = new TextEncoder().encode(process.env.JWT_SECRET || 'your-secret-key');

export interface User {
  id: string;
  email: string;
  name?: string;
  isSystemUser: boolean;
  isFirstLogin: boolean;
}

export async function createToken(user: User): Promise<string> {
  const token = await new SignJWT({
    id: user.id,
    email: user.email,
    isSystemUser: user.isSystemUser,
    isFirstLogin: user.isFirstLogin,
  })
    .setProtectedHeader({ alg: 'HS256' })
    .setIssuedAt()
    .setExpirationTime('24h')
    .sign(JWT_SECRET);

  return token;
}

export async function verifyToken(token: string): Promise<User> {
  try {
    const { payload } = await jwtVerify<User>(token, JWT_SECRET);

    // Verify necessary fields exist
    if (!payload.id || !payload.email || typeof payload.isSystemUser !== 'boolean' || typeof payload.isFirstLogin !== 'boolean') {
      throw new Error('Invalid token payload');
    }

    return {
      id: payload.id,
      email: payload.email,
      name: payload.name,
      isSystemUser: payload.isSystemUser,
      isFirstLogin: payload.isFirstLogin,
    };
  } catch (error) {
    throw new Error('Invalid token');
  }
}

// Get token from header
export function getTokenFromHeader(authHeader: string | null): string | null {
  if (!authHeader) return null;
  const [type, token] = authHeader.split(' ');
  if (type !== 'Bearer' || !token) return null;
  return token;
}
