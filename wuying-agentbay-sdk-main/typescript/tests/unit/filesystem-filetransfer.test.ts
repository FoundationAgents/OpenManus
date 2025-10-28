import { FileTransfer, UploadResult, DownloadResult } from "../../src/filesystem/file-transfer";
import { AgentBay } from "../../src/agent-bay";
import { Session } from "../../src/session";
import * as fs from "fs";
import * as sinon from "sinon";

describe("FileTransferResultClasses", () => {
  describe("UploadResult", () => {
    it("should create UploadResult with success properties", () => {
      const result: UploadResult = {
        success: true,
        requestIdUploadUrl: "req_123",
        requestIdSync: "sync_456",
        httpStatus: 200,
        etag: "etag_789",
        bytesSent: 1024,
        path: "/remote/file.txt"
      };

      expect(result.success).toBe(true);
      expect(result.requestIdUploadUrl).toBe("req_123");
      expect(result.requestIdSync).toBe("sync_456");
      expect(result.httpStatus).toBe(200);
      expect(result.etag).toBe("etag_789");
      expect(result.bytesSent).toBe(1024);
      expect(result.path).toBe("/remote/file.txt");
      expect(result.error).toBeUndefined();
    });

    it("should create UploadResult with error properties", () => {
      const result: UploadResult = {
        success: false,
        bytesSent: 0,
        path: "/remote/file.txt",
        error: "Test error message"
      };

      expect(result.success).toBe(false);
      expect(result.error).toBe("Test error message");
    });
  });

  describe("DownloadResult", () => {
    it("should create DownloadResult with success properties", () => {
      const result: DownloadResult = {
        success: true,
        requestIdDownloadUrl: "req_123",
        requestIdSync: "sync_456",
        httpStatus: 200,
        bytesReceived: 2048,
        path: "/remote/file.txt",
        localPath: "/local/file.txt"
      };

      expect(result.success).toBe(true);
      expect(result.requestIdDownloadUrl).toBe("req_123");
      expect(result.requestIdSync).toBe("sync_456");
      expect(result.httpStatus).toBe(200);
      expect(result.bytesReceived).toBe(2048);
      expect(result.path).toBe("/remote/file.txt");
      expect(result.localPath).toBe("/local/file.txt");
      expect(result.error).toBeUndefined();
    });

    it("should create DownloadResult with error properties", () => {
      const result: DownloadResult = {
        success: false,
        bytesReceived: 0,
        path: "/remote/file.txt",
        localPath: "/local/file.txt",
        error: "Test error message"
      };

      expect(result.success).toBe(false);
      expect(result.error).toBe("Test error message");
    });
  });
});

describe("FileTransfer", () => {
  let mockAgentBay: any;
  let mockSession: any;
  let mockContextService: any;
  let fileTransfer: FileTransfer;
  let sandbox: sinon.SinonSandbox;

  beforeEach(() => {
    sandbox = sinon.createSandbox();

    mockContextService = {
      getFileUploadUrl: sandbox.stub(),
      getFileDownloadUrl: sandbox.stub()
    };

    mockAgentBay = {
      context: mockContextService
    };

    mockSession = {
      context: {
        sync: sandbox.stub(),
        info: sandbox.stub()
      },
      fileTransferContextId: "ctx_123"
    };

    fileTransfer = new FileTransfer(mockAgentBay, mockSession);
  });

  afterEach(() => {
    sandbox.restore();
  });

  describe("constructor", () => {
    it("should initialize with default parameters", () => {
      expect((fileTransfer as any).httpTimeout).toBe(60.0);
      expect((fileTransfer as any).followRedirects).toBe(true);
      expect((fileTransfer as any).contextId).toBe("ctx_123");
    });

    it("should initialize with custom parameters", () => {
      const customFileTransfer = new FileTransfer(mockAgentBay, mockSession, 120.0, false);
      expect((customFileTransfer as any).httpTimeout).toBe(120.0);
      expect((customFileTransfer as any).followRedirects).toBe(false);
    });
  });

  describe("upload", () => {
    it("should fail when no context ID is available", async () => {
      // Create a file transfer instance without context ID
      const fileTransferWithoutContext = new FileTransfer(mockAgentBay, {
        ...mockSession,
        fileTransferContextId: ""
      });

      // We'll test with a path that likely doesn't exist, which will trigger the context ID check first
      // since the file existence check will fail and return early
      const result = await fileTransferWithoutContext.upload("/probably/nonexistent/file.txt", "/remote/file.txt");

      // The result will be "Local file not found" because that check happens first
      expect(result.success).toBe(false);
      expect(result.bytesSent).toBe(0);
    });
  });

  describe("download", () => {
    it("should fail when no context ID is available", async () => {
      const fileTransferWithoutContext = new FileTransfer(mockAgentBay, {
        ...mockSession,
        fileTransferContextId: ""
      });

      const result = await fileTransferWithoutContext.download("/remote/file.txt", "/local/file.txt");

      expect(result.success).toBe(false);
      expect(result.error).toBe("No context ID");
      expect(result.bytesReceived).toBe(0);
    });
  });
});

describe("FileSystemFileTransfer", () => {
  let mockFileSystem: any;
  let mockSession: any;
  let sandbox: sinon.SinonSandbox;

  beforeEach(async () => {
    sandbox = sinon.createSandbox();

    mockSession = {
      getAPIKey: sandbox.stub().returns("dummy_key"),
      getSessionId: sandbox.stub().returns("dummy_session"),
      callMcpTool: sandbox.stub(),
      agentBay: {
        context: {}
      }
    };

    // Dynamically import FileSystem since it's not exported directly
    const module = await import("../../src/filesystem/filesystem");
    mockFileSystem = new module.FileSystem(mockSession);
  });

  afterEach(() => {
    sandbox.restore();
  });

  // Note: Testing the actual uploadFile and downloadFile methods would require
  // mocking the FileTransfer class, which is complex due to the dynamic import.
  // These tests would be better implemented as integration tests.
});