import { AgentBay } from "../../src/agent-bay";
import { CreateSessionParams } from "../../src/session-params";
import { ContextSync } from "../../src/context-sync";
import * as fs from "fs";
import * as path from "path";
import * as os from "os";
import { log } from "../../src/utils/logger";

// Skip in CI if no API key, Jest will still collect but we handle at runtime
const apiKey = process.env.AGENTBAY_API_KEY || "";
log(`API Key: ${apiKey ? 'Present' : 'Missing'}`);
log(`CI Environment: ${process.env.CI ? 'Yes' : 'No'}`);

describe("File Transfer Integration", () => {
  let agentBay: AgentBay;
  let context: { id: string; name: string };
  let sessionId: string;
  let tempDir: string;
  let testContent: string;
  let remotePath: string;

  beforeAll(async () => {
    log("Starting beforeAll...");
    if (!apiKey || process.env.CI) {
      log("Skipping tests due to missing API key or CI environment");
      return;
    }
    log("Creating AgentBay instance...");
    agentBay = new AgentBay({ apiKey });

    const contextName = `file-transfer-test-${Date.now()}`;
    log(`Creating context: ${contextName}`);
    const contextResult = await agentBay.context.get(contextName, true);
    if (!contextResult.success || !contextResult.context) {
      throw new Error("Failed to create context");
    }

    context = contextResult.context as any;
    log(`Context created with ID: ${context.id}`);

    // Create browser session with context for testing
    const params = new CreateSessionParams();
    params.imageId = "browser_latest"; // Use browser image for more comprehensive testing
    // Add context sync for the test directory
    params.contextSync = [new ContextSync(context.id, "/tmp/file_transfer_test/")];

    log("Creating session...");
    const sessionResult = await agentBay.create(params);
    if (!sessionResult.success || !sessionResult.session) {
      throw new Error("Failed to create session");
    }

    sessionId = sessionResult.session.getSessionId();
    log(`Browser session created with ID: ${sessionId}`);

    // Create temporary directory for test files
    tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "file-transfer-test-"));
    log("beforeAll completed successfully");
  });

  afterAll(async () => {
    log("Starting afterAll...");
    if (!apiKey || process.env.CI) {
      log("Skipping cleanup due to missing API key or CI environment");
      return;
    }
    
    // Clean up temporary files
    if (tempDir && fs.existsSync(tempDir)) {
      fs.rmSync(tempDir, { recursive: true, force: true });
    }
    
    // Clean up session
    try {
      const listResult = await agentBay.list();
      if (listResult.sessionIds.includes(sessionId)) {
        const sessionResult = await agentBay.get(sessionId);
        if (sessionResult.success && sessionResult.session) {
          await agentBay.delete(sessionResult.session, true);
          log("Session successfully deleted with context sync");
        }
      }
    } catch (error) {
      log(`Warning: Error deleting session: ${error}`);
    }

    // Clean up context
    try {
      await agentBay.context.delete(context as any);
      log("Context successfully deleted");
    } catch (error) {
      log(`Warning: Error deleting context: ${error}`);
    }
    log("afterAll completed");
  });

  it("should upload files successfully", async () => {
    log("Starting upload test...");
    if (!apiKey || process.env.CI) {
      log("Skipping upload test due to missing API key or CI environment");
      return;
    }

    const sessionResult = await agentBay.get(sessionId);
    if (!sessionResult.success || !sessionResult.session) {
      throw new Error("Failed to get session");
    }
    const session = sessionResult.session;

    // Test file upload
    log("Testing file upload...");
        // Create test content
    testContent = "This is a test file for AgentBay FileTransfer upload integration test.\n".repeat(10);
    remotePath = "/tmp/file_transfer_test/upload_test.txt";
    
    const tempFilePath = path.join(tempDir, "upload_test.txt");
    fs.writeFileSync(tempFilePath, testContent);
    log(`Created test file at: ${tempFilePath}`);
    
    // Upload the file
    log("Calling uploadFile...");
    const uploadResult = await session.fileSystem.uploadFile(
      tempFilePath,
      remotePath
    );
    log(`Upload result: ${JSON.stringify(uploadResult, null, 2)}`);

    // Verify upload result
    expect(uploadResult.success).toBe(true);
    expect(uploadResult.bytesSent).toBeGreaterThan(0);
    expect(uploadResult.requestIdUploadUrl).toBeDefined();
    expect(uploadResult.requestIdSync).toBeDefined();

    log("Upload successful!");
    log(`Bytes sent: ${uploadResult.bytesSent}`);
    log(`Request ID (upload URL): ${uploadResult.requestIdUploadUrl}`);
    log(`Request ID (sync): ${uploadResult.requestIdSync}`);

    // Verify file exists in remote location by listing directory
    const dirListResult = await session.fileSystem.listDirectory("/tmp/file_transfer_test/");
    expect(dirListResult.success).toBe(true);
    expect(dirListResult.entries).toBeDefined();
    
    // Check if our uploaded file is in the directory listing
    const fileFound = dirListResult.entries.some((entry: any) => entry.name === 'upload_test.txt');
    expect(fileFound).toBe(true);

    log("File found in remote directory!");

    // Verify file content by reading it back
    const readResult = await session.fileSystem.readFile(remotePath);
    expect(readResult.success).toBe(true);
    expect(readResult.content).toBe(testContent);

    log("File content verified!");
  });

  it("should download files successfully", async () => {
    log("Starting download test...");
    if (!apiKey || process.env.CI) {
      log("Skipping download test due to missing API key or CI environment");
      return;
    }

    const sessionResult = await agentBay.get(sessionId);
    if (!sessionResult.success || !sessionResult.session) {
      throw new Error("Failed to get session");
    }
    const session = sessionResult.session;

    // First, create a file in the remote location
    const remotePath = "/tmp/file_transfer_test/download_test.txt";
    const testContent = "This is a test file for AgentBay FileTransfer download integration test.\n".repeat(15);
    
    log("Creating test directory...");
    const createDirResult = await session.fileSystem.createDirectory("/tmp/file_transfer_test/");
    log(`Create directory result: ${createDirResult.success}`);
    expect(createDirResult.success).toBe(true);
    
    const writeResult = await session.fileSystem.writeFile(remotePath, testContent);
    expect(writeResult.success).toBe(true);

    // Verify directory exists and list content
    const lsResult = await session.fileSystem.listDirectory("/tmp/file_transfer_test/");
    expect(lsResult.success).toBe(true);
    log(`Directory content: ${JSON.stringify(lsResult.entries, null, 2)}`);

    // Create a temporary file path for download
    const tempFilePath = path.join(tempDir, "download_test.txt");

    // Download the file
    log("Calling downloadFile...");
    const downloadResult = await session.fileSystem.downloadFile(
      remotePath,
      tempFilePath
    );
    log(`Download result: ${JSON.stringify(downloadResult, null, 2)}`);

    // Verify download result
    expect(downloadResult.success).toBe(true);
    expect(downloadResult.bytesReceived).toBeGreaterThan(0);
    expect(downloadResult.requestIdDownloadUrl).toBeDefined();
    expect(downloadResult.requestIdSync).toBeDefined();
    expect(downloadResult.localPath).toBe(tempFilePath);

    // Verify downloaded file content
    const downloadedContent = fs.readFileSync(tempFilePath, 'utf-8');
    log(`Downloaded file content length: ${downloadedContent.length} bytes`);
    expect(downloadedContent).toBe(testContent);

    log("Download test completed successfully!");
  });
});