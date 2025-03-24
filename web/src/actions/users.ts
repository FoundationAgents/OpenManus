'use server';

import { prisma } from '@/lib/prisma';
import { generateSalt, hashPassword } from '@/lib/password';
import { withSystemUserAuth, AuthUser } from '@/lib/auth-wrapper';

interface CreateUserParams {
  email: string;
  password: string;
  name?: string;
}

/**
 * Internal user creation function
 */
async function _createUser(user: AuthUser, params: CreateUserParams) {
  // Check if email already exists
  const existingUser = await prisma.users.findUnique({
    where: { email: params.email },
  });

  if (existingUser) {
    throw new Error('Email already exists');
  }

  // Create new user
  const salt = generateSalt();
  const hashedPassword = hashPassword(params.password, salt);

  const newUser = await prisma.users.create({
    data: {
      email: params.email,
      name: params.name,
      password: hashedPassword,
      salt,
      isSystemUser: false,
      isFirstLogin: true,
    },
  });

  await prisma.organizationUsers.create({
    data: {
      userId: newUser.id,
      organizationId: user.organizationId,
    },
  });

  return {
    id: newUser.id,
    email: newUser.email,
    name: newUser.name,
  };
}

/**
 * Create a new user
 * @param params User creation parameters
 * @returns Created user data
 */
export const createUser = withSystemUserAuth(_createUser);
