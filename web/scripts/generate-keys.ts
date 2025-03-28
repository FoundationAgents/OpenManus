import fs from 'fs';
import path from 'path';
import { generateKeyPair } from '../src/lib/crypto';

const KEYS_DIR = path.join(process.cwd(), 'keys');

if (!fs.existsSync(KEYS_DIR)) {
  fs.mkdirSync(KEYS_DIR);
}

const { publicKey, privateKey } = generateKeyPair();

fs.writeFileSync(path.join(KEYS_DIR, 'public.pem'), publicKey);
fs.writeFileSync(path.join(KEYS_DIR, 'private.pem'), privateKey);

console.log('RSA key pair generated successfully!');
console.log('Public key saved to: keys/public.pem');
console.log('Private key saved to: keys/private.pem');
