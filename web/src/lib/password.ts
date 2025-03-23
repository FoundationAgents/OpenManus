import { randomBytes, pbkdf2Sync } from 'crypto';

const SALT_LENGTH = 16;
const ITERATIONS = 10000;
const KEY_LENGTH = 64;
const DIGEST = 'sha512';

// Default system user credentials
const DEFAULT_SYSTEM_USER = {
  email: 'admin@openmanus.com',
  salt: 'salt',
  password: 'admin',
};

// System user configuration
export const SYSTEM_USER = {
  email: process.env.SYSTEM_USER_EMAIL || DEFAULT_SYSTEM_USER.email,
  salt: process.env.SYSTEM_USER_SALT || DEFAULT_SYSTEM_USER.salt,
  passwordHash: process.env.SYSTEM_USER_PASSWORD_HASH || hashPassword(DEFAULT_SYSTEM_USER.password, DEFAULT_SYSTEM_USER.salt),
};

export function generateSalt(): string {
  return randomBytes(SALT_LENGTH).toString('hex');
}

export function hashPassword(password: string, salt: string): string {
  return pbkdf2Sync(password, salt, ITERATIONS, KEY_LENGTH, DIGEST).toString('hex');
}

export function verifyPassword(password: string, salt: string, hashedPassword: string): boolean {
  const hash = hashPassword(password, salt);
  return hash === hashedPassword;
}
