import crypto from 'crypto';

/**
 * encrypt data with public key
 * rsa encrypt only support string which length less than 214 bytes
 * @param data - data to encrypt
 * @param publicKey - public key
 * @returns encrypted data
 */
export function encryptWithPublicKey(data: string, publicKey: string): string {
  if (data.length > 214) {
    throw new Error('Data is too long to encrypt with public key, please use encryptLongTextWithPublicKey instead');
  }

  const buffer = Buffer.from(data, 'utf8');
  const encrypted = crypto.publicEncrypt(
    {
      key: publicKey,
      padding: crypto.constants.RSA_PKCS1_OAEP_PADDING,
      oaepHash: 'sha256',
    },
    buffer,
  );
  return encrypted.toString('base64');
}

export function decryptWithPrivateKey(encryptedData: string, privateKey: string): string {
  const buffer = Buffer.from(encryptedData, 'base64');
  const decrypted = crypto.privateDecrypt(
    {
      key: privateKey,
      padding: crypto.constants.RSA_PKCS1_OAEP_PADDING,
      oaepHash: 'sha256',
    },
    buffer,
  );
  return decrypted.toString('utf8');
}

// generate aes key
function generateAESKey(): Buffer {
  return crypto.randomBytes(32); // 256 bits
}

// generate iv
function generateIV(): Buffer {
  return crypto.randomBytes(12); // 96 bits for GCM
}

// encrypt with aes-256-gcm
function encryptWithAES(data: Buffer, key: Buffer): { encrypted: Buffer; iv: Buffer; authTag: Buffer } {
  const iv = generateIV();
  const cipher = crypto.createCipheriv('aes-256-gcm', key, iv);
  const encrypted = Buffer.concat([cipher.update(data), cipher.final()]);
  return {
    encrypted,
    iv,
    authTag: cipher.getAuthTag(),
  };
}

// decrypt with aes-256-gcm
function decryptWithAES(encrypted: Buffer, key: Buffer, iv: Buffer, authTag: Buffer): Buffer {
  const decipher = crypto.createDecipheriv('aes-256-gcm', key, iv);
  decipher.setAuthTag(authTag);
  return Buffer.concat([decipher.update(encrypted), decipher.final()]);
}

// new encrypt function, use hybrid encryption scheme
export function encryptLongTextWithPublicKey(data: string, publicKey: string): string {
  const dataBuffer = Buffer.from(data, 'utf8');

  // generate aes key
  const aesKey = generateAESKey();

  // encrypt with aes-256-gcm
  const { encrypted, iv, authTag } = encryptWithAES(dataBuffer, aesKey);

  // encrypt aes key with rsa
  const encryptedKey = crypto.publicEncrypt(
    {
      key: publicKey,
      padding: crypto.constants.RSA_PKCS1_OAEP_PADDING,
      oaepHash: 'sha256',
    },
    aesKey,
  );

  // combine all data into an object and serialize
  const result = {
    version: 2, // new version identifier
    encryptedKey: encryptedKey.toString('base64'),
    encrypted: encrypted.toString('base64'),
    iv: iv.toString('base64'),
    authTag: authTag.toString('base64'),
  };

  return JSON.stringify(result);
}

// decrypt function, support both new and old formats
export function decryptLongTextWithPrivateKey(encryptedData: string, privateKey: string): string {
  try {
    // try to parse as new encrypted format
    const data = JSON.parse(encryptedData);

    if (data.version === 2) {
      // new format: hybrid encryption
      const encryptedKey = Buffer.from(data.encryptedKey, 'base64');
      const encrypted = Buffer.from(data.encrypted, 'base64');
      const iv = Buffer.from(data.iv, 'base64');
      const authTag = Buffer.from(data.authTag, 'base64');

      // decrypt aes key with rsa
      const aesKey = crypto.privateDecrypt(
        {
          key: privateKey,
          padding: crypto.constants.RSA_PKCS1_OAEP_PADDING,
          oaepHash: 'sha256',
        },
        encryptedKey,
      );

      // decrypt with aes-256-gcm
      const decrypted = decryptWithAES(encrypted, aesKey, iv, authTag);
      return decrypted.toString('utf8');
    }
  } catch (e) {
    // if not new format, try old format
    console.warn('Long text decrypt is not supported, try old format');
    return decryptWithPrivateKey(encryptedData, privateKey);
  }

  throw new Error('Invalid encrypted data format');
}
