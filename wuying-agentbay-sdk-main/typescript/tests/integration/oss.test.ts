import { AgentBay, Session } from "../../src";
import { getTestApiKey, containsToolNotFound } from "../utils/test-helpers";
import { log } from "../../src/utils/logger";

// Helper function to get OSS credentials from environment variables or use defaults
function getOssCredentials(): {
  accessKeyId: string;
  accessKeySecret: string;
  securityToken: string;
  endpoint: string;
  region: string;
} {
  const accessKeyId = process.env.OSS_ACCESS_KEY_ID || "your-access-key-id";
  const accessKeySecret =
    process.env.OSS_ACCESS_KEY_SECRET || "your-access-key-secret";
  const securityToken = process.env.OSS_SECURITY_TOKEN || "your-security-token";
  const endpoint =
    process.env.OSS_ENDPOINT || "https://oss-cn-hangzhou.aliyuncs.com";
  const region = process.env.OSS_REGION || "cn-hangzhou";

  if (!process.env.OSS_ACCESS_KEY_ID) {
    log("OSS_ACCESS_KEY_ID environment variable not set, using default value");
  }
  if (!process.env.OSS_ACCESS_KEY_SECRET) {
    log(
      "OSS_ACCESS_KEY_SECRET environment variable not set, using default value"
    );
  }
  if (!process.env.OSS_SECURITY_TOKEN) {
    log("OSS_SECURITY_TOKEN environment variable not set, using default value");
  }
  if (!process.env.OSS_ENDPOINT) {
    log("OSS_ENDPOINT environment variable not set, using default value");
  }
  if (!process.env.OSS_REGION) {
    log("OSS_REGION environment variable not set, using default value");
  }

  return {
    accessKeyId,
    accessKeySecret,
    securityToken,
    endpoint,
    region,
  };
}

// Helper function to check if content has error
function hasErrorInContent(content: any[] | string): boolean {
  // If content is a string, check if it contains error text
  if (typeof content === "string") {
    return content.toLowerCase().includes("error");
  }

  // If content is not an array, consider it an error
  if (!Array.isArray(content)) {
    return true;
  }

  // If content is an empty array, consider it an error
  if (content.length === 0) {
    return true;
  }

  // Check if any content item has error text
  return content.some(
    (item) =>
      item &&
      typeof item === "object" &&
      item.text &&
      typeof item.text === "string" &&
      item.text.toLowerCase().includes("error")
  );
}

describe("OSS", () => {
  let agentBay: AgentBay;
  let session: Session;

  beforeEach(async () => {
    const apiKey = getTestApiKey();
    log(apiKey);
    agentBay = new AgentBay({ apiKey });

    // Create a session
    log("Creating a new session for OSS testing...");
    const createResponse = await agentBay.create({ imageId: "code_latest" });
    session = createResponse.session;
    log(`Session created with ID: ${session.sessionId}`);
    log(`Create Session RequestId: ${createResponse.requestId || "undefined"}`);
  });

  afterEach(async () => {
    // Clean up the session
    log("Cleaning up: Deleting the session...");
    try {
      if (session) {
        const deleteResponse = await agentBay.delete(session);
        log(
          `Delete Session RequestId: ${deleteResponse.requestId || "undefined"}`
        );
      }
    } catch (error) {
      log(`Warning: Error deleting session: ${error}`);
    }
  });

  describe("envInit", () => {
    it.only("should initialize OSS environment", async () => {
      if (session.oss) {
        // Get OSS credentials from environment variables
        const {
          accessKeyId,
          accessKeySecret,
          securityToken,
          endpoint,
          region,
        } = getOssCredentials();

        log("Initializing OSS environment...");
        try {
          const envInitResponse = await session.oss.envInit(
            accessKeyId,
            accessKeySecret,
            securityToken,
            endpoint,
            region
          );
          log(`EnvInit clientConfig:`, envInitResponse.clientConfig);
          log(`EnvInit RequestId: ${envInitResponse.requestId || "undefined"}`);

          // Verify that the response contains requestId
          expect(envInitResponse.requestId).toBeDefined();
          expect(typeof envInitResponse.requestId).toBe("string");

          // Check success status
          expect(envInitResponse.success).toBe(true);

          // Check if clientConfig is defined
          expect(envInitResponse.clientConfig).toBeDefined();
          expect(typeof envInitResponse.clientConfig).toBe("object");

          // If there's an error, it should not be successful
          if (envInitResponse.errorMessage) {
            expect(envInitResponse.success).toBe(false);
          }

          log("OSS environment initialization successful");
        } catch (error) {
          log(`OSS environment initialization failed: ${error}`);
          throw error;
        }
      } else {
        log("Note: OSS interface is nil, skipping OSS test");
      }
    });
  });

  describe("upload", () => {
    it.only("should upload a file to OSS", async () => {
      if (session.oss && session.fileSystem) {
        // First initialize the OSS environment
        const {
          accessKeyId,
          accessKeySecret,
          securityToken,
          endpoint,
          region,
        } = getOssCredentials();
        const envInitResponse = await session.oss.envInit(
          accessKeyId,
          accessKeySecret,
          securityToken,
          endpoint,
          region
        );
        log(`EnvInit RequestId: ${envInitResponse.requestId || "undefined"}`);

        // Create a test file to upload
        const testContent = "This is a test file for OSS upload.";
        const testFilePath = "/tmp/test_oss_upload.txt";
        const writeResponse = await session.fileSystem.writeFile(
          testFilePath,
          testContent
        );
        log(`Write File RequestId: ${writeResponse.requestId || "undefined"}`);

        log("Uploading file to OSS...");
        const bucket = process.env.OSS_TEST_BUCKET || "your-bucket-name";
        const objectKey = "your-object-key";

        try {
          const uploadResponse = await session.oss.upload(
            bucket,
            objectKey,
            testFilePath
          );
          log(`Upload content:`, uploadResponse.content);
          log(`Upload RequestId: ${uploadResponse.requestId || "undefined"}`);

          // Verify that the response contains requestId
          expect(uploadResponse.requestId).toBeDefined();
          expect(typeof uploadResponse.requestId).toBe("string");

          // Check success status
          expect(uploadResponse.success).toBe(true);

          // Check if content is defined
          expect(uploadResponse.content).toBeDefined();
          expect(typeof uploadResponse.content).toBe("string");
          expect(hasErrorInContent(uploadResponse.content)).toBe(false);

          // If there's an error, it should not be successful
          if (uploadResponse.errorMessage) {
            expect(uploadResponse.success).toBe(false);
          }

          log("OSS upload successful");
        } catch (error) {
          log(`OSS upload failed: ${error}`);
          throw error;
        }
      } else {
        log("Note: OSS or fileSystem interface is nil, skipping OSS test");
      }
    });
  });

  describe("uploadAnonymous", () => {
    it.only("should upload a file anonymously", async () => {
      if (session.oss && session.fileSystem) {
        // Create a test file to upload
        const testContent = "This is a test file for OSS anonymous upload.";
        const testFilePath = "/tmp/test_oss_upload_anon.txt";
        const writeResponse = await session.fileSystem.writeFile(
          testFilePath,
          testContent
        );
        log(`Write File RequestId: ${writeResponse.requestId || "undefined"}`);

        log("Uploading file anonymously...");
        const uploadUrl =
          process.env.OSS_TEST_UPLOAD_URL ||
          "https://example.com/upload/test-file.txt";

        try {
          const uploadAnonResponse = await session.oss.uploadAnonymous(
            uploadUrl,
            testFilePath
          );
          log(`UploadAnonymous content:`, uploadAnonResponse.content);
          log(
            `UploadAnonymous RequestId: ${
              uploadAnonResponse.requestId || "undefined"
            }`
          );

          // Verify that the response contains requestId
          expect(uploadAnonResponse.requestId).toBeDefined();
          expect(typeof uploadAnonResponse.requestId).toBe("string");

          // Check success status
          expect(uploadAnonResponse.success).toBe(true);

          // Check if content is defined
          expect(uploadAnonResponse.content).toBeDefined();
          expect(typeof uploadAnonResponse.content).toBe("string");
          expect(
            uploadAnonResponse.content.toLowerCase().includes("error")
          ).toBe(false);

          // If there's an error, it should not be successful
          if (uploadAnonResponse.errorMessage) {
            expect(uploadAnonResponse.success).toBe(false);
          }

          log("OSS anonymous upload successful");
        } catch (error) {
          log(`OSS anonymous upload failed: ${error}`);
          throw error;
        }
      } else {
        log("Note: OSS or fileSystem interface is nil, skipping OSS test");
      }
    });
  });

  describe("download", () => {
    it.only("should download a file from OSS", async () => {
      if (session.oss && session.fileSystem) {
        // First initialize the OSS environment
        const {
          accessKeyId,
          accessKeySecret,
          securityToken,
          endpoint,
          region,
        } = getOssCredentials();
        const envInitResponse = await session.oss.envInit(
          accessKeyId,
          accessKeySecret,
          securityToken,
          endpoint,
          region
        );
        log(`EnvInit RequestId: ${envInitResponse.requestId || "undefined"}`);

        log("Downloading file from OSS...");
        const bucket = process.env.OSS_TEST_BUCKET || "your-bucket-name";
        const objectKey = "your-object-key";
        const downloadPath = "/tmp/test_oss_download.txt";

        try {
          const downloadResponse = await session.oss.download(
            bucket,
            objectKey,
            downloadPath
          );
          log(`Download content:`, downloadResponse.content);
          log(
            `Download RequestId: ${downloadResponse.requestId || "undefined"}`
          );

          // Verify that the response contains requestId
          expect(downloadResponse.requestId).toBeDefined();
          expect(typeof downloadResponse.requestId).toBe("string");

          // Check success status
          expect(downloadResponse.success).toBe(true);

          // Check if content is defined
          expect(downloadResponse.content).toBeDefined();
          expect(typeof downloadResponse.content).toBe("string");
          expect(hasErrorInContent(downloadResponse.content)).toBe(false);

          // If there's an error, it should not be successful
          if (downloadResponse.errorMessage) {
            expect(downloadResponse.success).toBe(false);
          }

          log("OSS download successful");

          // Verify the downloaded file exists
          const fileInfoResponse = await session.fileSystem.getFileInfo(
            downloadPath
          );
          log(`Downloaded file info:`, fileInfoResponse.fileInfo);
          log(
            `Get File Info RequestId: ${
              fileInfoResponse.requestId || "undefined"
            }`
          );
          expect(fileInfoResponse.fileInfo).toBeDefined();
        } catch (error) {
          log(`OSS download failed: ${error}`);
          throw error;
        }
      } else {
        log("Note: OSS or fileSystem interface is nil, skipping OSS test");
      }
    });
  });

  describe("downloadAnonymous", () => {
    it.only("should download a file anonymously", async () => {
      if (session.oss && session.fileSystem) {
        log("Downloading file anonymously...");
        const downloadUrl =
          process.env.OSS_TEST_DOWNLOAD_URL ||
          "https://example.com/download/test-file.txt";
        const downloadPath = "/tmp/test_oss_download_anon.txt";

        try {
          const downloadAnonResponse = await session.oss.downloadAnonymous(
            downloadUrl,
            downloadPath
          );
          log(`DownloadAnonymous content:`, downloadAnonResponse.content);
          log(
            `DownloadAnonymous RequestId: ${
              downloadAnonResponse.requestId || "undefined"
            }`
          );

          // Verify that the response contains requestId
          expect(downloadAnonResponse.requestId).toBeDefined();
          expect(typeof downloadAnonResponse.requestId).toBe("string");

          // Check success status
          expect(downloadAnonResponse.success).toBe(true);

          // Check if content is defined
          expect(downloadAnonResponse.content).toBeDefined();
          expect(typeof downloadAnonResponse.content).toBe("string");
          expect(
            downloadAnonResponse.content.toLowerCase().includes("error")
          ).toBe(false);

          // If there's an error, it should not be successful
          if (downloadAnonResponse.errorMessage) {
            expect(downloadAnonResponse.success).toBe(false);
          }

          log("OSS anonymous download successful");

          // Verify the downloaded file exists
          const fileInfoResponse = await session.fileSystem.getFileInfo(
            downloadPath
          );
          log(`Downloaded file info:`, fileInfoResponse.fileInfo);
          log(
            `Get File Info RequestId: ${
              fileInfoResponse.requestId || "undefined"
            }`
          );
          expect(fileInfoResponse.fileInfo).toBeDefined();
        } catch (error) {
          log(`OSS anonymous download failed: ${error}`);
          throw error;
        }
      } else {
        log("Note: OSS or fileSystem interface is nil, skipping OSS test");
      }
    });
  });
});
