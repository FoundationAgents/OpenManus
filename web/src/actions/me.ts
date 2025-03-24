'use server';

import { prisma } from '@/lib/prisma';
import { verifyPassword, hashPassword } from '@/lib/password';
import { withUserAuth } from '@/lib/auth-wrapper';

/**
 * Modify password
 * @param oldPassword Current password
 * @param newPassword New password
 * @returns Update result
 */
export const modifyPassword = withUserAuth<{ oldPassword: string; newPassword: string }>(async ({ user, args }) => {
  const { oldPassword, newPassword } = args;
  const dbUser = await prisma.users.findUnique({
    where: { id: user.id },
  });

  if (!dbUser) {
    throw new Error('User not found');
  }

  if (!verifyPassword(oldPassword, dbUser.password)) {
    throw new Error('Invalid old password');
  }

  const newHashedPassword = hashPassword(newPassword);

  await prisma.users.update({
    where: { id: user.id },
    data: {
      password: newHashedPassword,
      isFirstLogin: false,
    },
  });

  return { message: 'Password updated successfully' };
});

export const getMe = withUserAuth(async ({ user, organization }) => {
  if (!user.id) {
    throw new Error('User not found');
  }

  if (!organization) {
    throw new Error('Organization not found');
  }

  return {
    id: user.id,
    email: user.email,
    name: user.name,
    organizationId: organization.id,
    organizationName: organization.name,
  };
});
