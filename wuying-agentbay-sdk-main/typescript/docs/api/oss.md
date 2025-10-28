# OSS API Reference

The OSS (Object Storage Service) module provides functionality for interacting with cloud storage services.

## 📖 Related Tutorial

- [OSS Integration Guide](../../../docs/guides/common-features/advanced/oss-integration.md) - Detailed tutorial on integrating with Object Storage Service

## OSS Class

The `OSS` class provides methods for OSS operations.

### envInit

Initializes OSS environment variables with the specified credentials.

```typescript
async envInit(
  accessKeyId: string,
  accessKeySecret: string,
  securityToken: string,
  endpoint?: string,
  region?: string
): Promise<OSSClientResult>
```

**Parameters:**
- `accessKeyId`: The Access Key ID for OSS authentication.
- `accessKeySecret`: The Access Key Secret for OSS authentication.
- `securityToken`: The security token for OSS authentication.
- `endpoint`: The OSS service endpoint. If not specified, the default is used.
- `region`: The OSS region. If not specified, the default is used.

**Returns:**
- `Promise<OSSClientResult>`: Result object containing client configuration, request ID, success status, and error message if any.

**Throws:**
- `APIError`: If the environment initialization fails.

**Example:**
```typescript
import { AgentBay } from 'wuying-agentbay-sdk';

// Initialize the SDK
const agentBay = new AgentBay({ apiKey: 'your_api_key' });

// Initialize OSS environment
async function initializeOSS() {
  try {
    const result = await agentBay.oss.envInit(
      'your_access_key_id',
      'your_access_key_secret',
      'your_security_token',
      'oss-cn-hangzhou.aliyuncs.com',
      'cn-hangzhou'
    );
    console.log('OSS environment initialized successfully:', result);
  } catch (error) {
    console.error('Error initializing OSS environment:', error);
  }
}

initializeOSS();
```


### upload

**Note:** Before calling this API, you must call `envInit` to initialize the OSS environment.

Uploads a local file or directory to OSS.

```typescript
async upload(bucket: string, object: string, path: string): Promise<string>
```

**Parameters:**
- `bucket`: OSS bucket name.
- `object`: Object key in OSS.
- `path`: Local file or directory path to upload.

**Returns:**
- `Promise<string>`: The result of the upload operation.

**Throws:**
- `APIError`: If the upload fails.

**Example:**
```typescript
import { AgentBay } from 'wuying-agentbay-sdk';

// Initialize the SDK
const agentBay = new AgentBay({ apiKey: 'your_api_key' });

async function uploadFile() {
  try {
    // Step 1: Initialize OSS environment
    await agentBay.oss.envInit(
      'your_access_key_id',
      'your_access_key_secret',
      'your_security_token',
      'oss-cn-hangzhou.aliyuncs.com',
      'cn-hangzhou'
    );
    // Step 2: Upload file to OSS
    const result = await agentBay.oss.upload('my-bucket', 'my-object', '/path/to/local/file');
    console.log('File uploaded successfully:', result);
  } catch (error) {
    console.error('Error uploading file:', error);
  }
}

uploadFile();
```

### uploadAnonymous

**Note:** Before calling this API, you must call `envInit` to initialize the OSS environment.

Uploads a local file or directory to a URL anonymously.

```typescript
async uploadAnonymous(url: string, path: string): Promise<string>
```

**Parameters:**
- `url`: The HTTP/HTTPS URL to upload the file to.
- `path`: Local file or directory path to upload.

**Returns:**
- `Promise<string>`: The result of the upload operation.

**Throws:**
- `APIError`: If the upload fails.

**Example:**
```typescript
import { AgentBay } from 'wuying-agentbay-sdk';

// Initialize the SDK
const agentBay = new AgentBay({ apiKey: 'your_api_key' });

async function uploadFileAnonymously() {
  try {
    // Step 1: Initialize OSS environment
    await agentBay.oss.envInit(
      'your_access_key_id',
      'your_access_key_secret',
      'your_security_token',
      'oss-cn-hangzhou.aliyuncs.com',
      'cn-hangzhou'
    );
    // Step 2: Upload file anonymously
    const result = await agentBay.oss.uploadAnonymous('https://example.com/upload', '/path/to/local/file');
    console.log('File uploaded anonymously successfully:', result);
  } catch (error) {
    console.error('Error uploading file anonymously:', error);
  }
}

uploadFileAnonymously();
```

### download

**Note:** Before calling this API, you must call `envInit` to initialize the OSS environment.

Downloads an object from OSS to a local file.

```typescript
async download(bucket: string, object: string, path: string): Promise<string>
```

**Parameters:**
- `bucket`: OSS bucket name.
- `object`: Object key in OSS.
- `path`: Local path to save the downloaded file.

**Returns:**
- `Promise<string>`: The result of the download operation.

**Throws:**
- `APIError`: If the download fails.

**Example:**
```typescript
import { AgentBay } from 'wuying-agentbay-sdk';

// Initialize the SDK
const agentBay = new AgentBay({ apiKey: 'your_api_key' });

async function downloadFile() {
  try {
    // Step 1: Initialize OSS environment
    await agentBay.oss.envInit(
      'your_access_key_id',
      'your_access_key_secret',
      'your_security_token',
      'oss-cn-hangzhou.aliyuncs.com',
      'cn-hangzhou'
    );
    // Step 2: Download file from OSS
    const result = await agentBay.oss.download('my-bucket', 'my-object', '/path/to/local/file');
    console.log('File downloaded successfully:', result);
  } catch (error) {
    console.error('Error downloading file:', error);
  }
}

downloadFile();
```

### downloadAnonymous

**Note:** Before calling this API, you must call `envInit` to initialize the OSS environment.

Downloads a file from a URL anonymously to a local file.

```typescript
async downloadAnonymous(url: string, path: string): Promise<string>
```

**Parameters:**
- `url`: The HTTP/HTTPS URL to download the file from.
- `path`: The full local file path to save the downloaded file.

**Returns:**
- `Promise<string>`: The result of the download operation.

**Throws:**
- `APIError`: If the download fails.

**Example:**
```typescript
import { AgentBay } from 'wuying-agentbay-sdk';

// Initialize the SDK
const agentBay = new AgentBay({ apiKey: 'your_api_key' });

async function downloadFileAnonymously() {
  try {
    // Step 1: Initialize OSS environment
    await agentBay.oss.envInit(
      'your_access_key_id',
      'your_access_key_secret',
      'your_security_token',
      'oss-cn-hangzhou.aliyuncs.com',
      'cn-hangzhou'
    );
    // Step 2: Download file anonymously
    const result = await agentBay.oss.downloadAnonymous('https://example.com/file.txt', '/path/to/local/file.txt');
    console.log('File downloaded anonymously successfully:', result);
  } catch (error) {
    console.error('Error downloading file anonymously:', error);
  }
}

downloadFileAnonymously();
```

## Related Resources

- [Filesystem API Reference](filesystem.md)
- [Session API Reference](session.md)