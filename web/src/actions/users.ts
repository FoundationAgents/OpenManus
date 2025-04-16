'use server';

import { prisma } from '@/lib/prisma';
import { hashPassword } from '@/lib/password';
import { AuthWrapperContext, withUserAuth } from '@/lib/auth-wrapper';

/**
 * Create a new user
 * @param params User creation parameters
 * @returns Created user data
 */
export const createUser = withUserAuth(async ({ organization, args }: AuthWrapperContext<{ email: string; name: string; password: string }>) => {
  const { email, password, name } = args;
  // Check if email already exists
  return await prisma.$transaction(async tx => {
    const existingUser = await tx.users.findUnique({
      where: { email },
    });

    if (existingUser) {
      throw new Error('Email already exists');
    }

    // Create new user
    const hashedPassword = hashPassword(password);

    const newUser = await tx.users.create({
      data: { email, name, password: hashedPassword, isFirstLogin: true },
    });

    await tx.organizationUsers.create({
      data: {
        userId: newUser.id,
        organizationId: organization.id,
      },
    });

    return {
      id: newUser.id,
      email: newUser.email,
      name: newUser.name,
    };
  });
});
