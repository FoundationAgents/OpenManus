import { NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';
import { verifyPassword } from '@/lib/password';
import { createToken } from '@/lib/auth';

export async function POST(request: Request) {
  try {
    const { email, password } = await request.json();

    const user = await prisma.users.findUnique({
      where: { email },
    });

    if (!user) {
      return NextResponse.json({ error: 'User not found' }, { status: 404 });
    }

    if (!verifyPassword(password, user.password)) {
      return NextResponse.json({ error: 'Invalid credentials' }, { status: 401 });
    }

    const organizationUsers = await prisma.organizationUsers.findMany({
      where: { userId: user.id },
    });
    if (organizationUsers.length === 0) {
      return NextResponse.json({ error: 'User not associated with any organization' }, { status: 401 });
    }

    // TODO: Multi-tenant mode is not supported yet, return error if user is associated with multiple organizations
    if (organizationUsers.length > 1) {
      return NextResponse.json({ error: 'User is associated with multiple organizations' }, { status: 401 });
    }
    const organization = await prisma.organizations.findUnique({ where: { id: organizationUsers[0].organizationId } });

    if (!organization) {
      return NextResponse.json({ error: 'Organization not found' }, { status: 404 });
    }

    const token = await createToken({
      id: user.id,
      email: user.email,
      name: user.name || undefined,
      isFirstLogin: user.isFirstLogin,
    });

    return NextResponse.json({ token });
  } catch (error) {
    console.error('Login error:', error);
    return NextResponse.json({ error: 'Login failed' }, { status: 500 });
  }
}
