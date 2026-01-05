import bcrypt from 'bcryptjs';

const SALT_ROUNDS = 10;

export function hashPassword(password: string): string {
  return bcrypt.hashSync(password, SALT_ROUNDS);
}

export function verifyPassword(password: string, hashedPassword: string): boolean {
  return bcrypt.compareSync(password, hashedPassword);
}
