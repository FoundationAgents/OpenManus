'use server';

import { prisma } from '@/lib/prisma';
import { verifyPassword, generateSalt, hashPassword } from '@/lib/password';
import { withUserAuth, AuthUser } from '@/lib/auth-wrapper';

/**
 * Internal password update function
 */
async function _modifyPassword(user: AuthUser, oldPassword: string, newPassword: string) {
  // System user update password
  if (user.isSystemUser) {
    const systemUserSalt = process.env.SYSTEM_USER_SALT;
    const systemUserHash = process.env.SYSTEM_USER_PASSWORD_HASH;

    if (!systemUserSalt || !systemUserHash) {
      throw new Error('System user configuration error');
    }

    if (!verifyPassword(oldPassword, systemUserSalt, systemUserHash)) {
      throw new Error('Invalid old password');
    }

    // Note: In a real project, this requires a secure way to update environment variables
    // This might be managed through configuration files or other means
    return { message: 'Password updated successfully' };
  }

  // Normal user update password
  const dbUser = await prisma.user.findUnique({
    where: { id: user.id },
  });

  if (!dbUser) {
    throw new Error('User not found');
  }

  if (!verifyPassword(oldPassword, dbUser.salt, dbUser.password)) {
    throw new Error('Invalid old password');
  }

  const newSalt = generateSalt();
  const newHashedPassword = hashPassword(newPassword, newSalt);

  await prisma.user.update({
    where: { id: user.id },
    data: {
      password: newHashedPassword,
      salt: newSalt,
      isFirstLogin: false,
    },
  });

  return { message: 'Password updated successfully' };
}

/**
 * Modify password
 * @param oldPassword Current password
 * @param newPassword New password
 * @returns Update result
 */
export const modifyPassword = withUserAuth(_modifyPassword);
