import { NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';
import { verifyPassword, SYSTEM_USER } from '@/lib/password';
import { createToken } from '@/lib/auth';

export async function POST(request: Request) {
  try {
    const { email, password } = await request.json();

    // Check if it's a system user
    if (email === SYSTEM_USER.email) {
      if (verifyPassword(password, SYSTEM_USER.salt, SYSTEM_USER.passwordHash)) {
        const token = await createToken({
          id: 'system',
          email,
          isSystemUser: true,
          isFirstLogin: false,
        });

        return NextResponse.json({ token });
      }
      return NextResponse.json({ error: 'Invalid credentials' }, { status: 401 });
    }

    // Normal user login
    const user = await prisma.users.findUnique({
      where: { email },
    });

    if (!user) {
      return NextResponse.json({ error: 'User not found' }, { status: 404 });
    }

    if (!verifyPassword(password, user.salt, user.password)) {
      return NextResponse.json({ error: 'Invalid credentials' }, { status: 401 });
    }

    const token = await createToken({
      id: user.id,
      email: user.email,
      name: user.name || undefined,
      isSystemUser: user.isSystemUser,
      isFirstLogin: user.isFirstLogin,
    });

    return NextResponse.json({ token });
  } catch (error) {
    console.error('Login error:', error);
    return NextResponse.json({ error: 'Login failed' }, { status: 500 });
  }
}
