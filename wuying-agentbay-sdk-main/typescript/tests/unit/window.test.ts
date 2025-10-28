import { AgentBay, Session } from "../../src";
import { Window, WindowManager } from "../../src/window/window";
import { log } from "../../src/utils/logger";
import * as sinon from "sinon";

// Mock data for tests
const mockWindows: Window[] = [
  {
    window_id: 1,
    title: "Test Window 1",
    absolute_upper_left_x: 100,
    absolute_upper_left_y: 100,
    width: 800,
    height: 600,
    pid: 1234,
    pname: "test_app",
  },
  {
    window_id: 2,
    title: "Test Window 2",
    absolute_upper_left_x: 200,
    absolute_upper_left_y: 200,
    width: 1024,
    height: 768,
    pid: 5678,
    pname: "another_app",
  },
];

const mockActiveWindow: Window = mockWindows[0];

describe("WindowManager", () => {
  let windowManager: WindowManager;
  let mockSession: any;
  let callMcpToolStub: sinon.SinonStub;

  beforeEach(() => {
    // Create mock session with callMcpTool method
    mockSession = {
      getAPIKey: sinon.stub().returns("mock-api-key"),
      getSessionId: sinon.stub().returns("mock-session-id"),
      callMcpTool: sinon.stub(),
    };

    // Get reference to the callMcpTool stub for easier access
    callMcpToolStub = mockSession.callMcpTool;

    // Create WindowManager with mock session
    windowManager = new WindowManager(mockSession);

    log("WindowManager created with mock session");
  });

  afterEach(() => {
    sinon.restore();
  });

  describe("listRootWindows()", () => {
    it("should return a list of root windows with requestId", async () => {
      log("Testing listRootWindows...");

      // Setup mock response - new format for session.callMcpTool
      const mockResponse = {
        success: true,
        data: JSON.stringify(mockWindows),
        errorMessage: "",
        requestId: "mock-request-id-list",
      };

      callMcpToolStub.resolves(mockResponse);

      // Call the method
      const windowsResponse = await windowManager.listRootWindows();
      log(`Retrieved ${windowsResponse.windows.length} root windows`);
      log(
        `List Root Windows RequestId: ${
          windowsResponse.requestId || "undefined"
        }`
      );

      // Verify WindowListResult structure
      expect(windowsResponse.success).toBe(true);
      expect(windowsResponse.requestId).toBeDefined();
      expect(typeof windowsResponse.requestId).toBe("string");
      expect(windowsResponse.requestId).toBe("mock-request-id-list");
      expect(windowsResponse.errorMessage).toBeUndefined();

      // Verify windows array
      expect(windowsResponse.windows).toBeDefined();
      expect(Array.isArray(windowsResponse.windows)).toBe(true);
      expect(windowsResponse.windows.length).toBe(2);

      // Verify first window structure
      const firstWindow = windowsResponse.windows[0];
      expect(firstWindow.window_id).toBe(1);
      expect(firstWindow.title).toBe("Test Window 1");
      expect(firstWindow.width).toBe(800);
      expect(firstWindow.height).toBe(600);
    });

    it("should handle list root windows failure", async () => {
      // Use rejects for error simulation
      callMcpToolStub.rejects(new Error("Failed to list root windows"));

      const result = await windowManager.listRootWindows();

      // Verify error result structure
      expect(result.success).toBe(false);
      expect(result.requestId).toBe("");
      expect(result.windows).toEqual([]);
      expect(result.errorMessage).toContain("Failed to list root windows");
    });
  });

  describe("getActiveWindow()", () => {
    it("should return the active window with requestId", async () => {
      log("Testing getActiveWindow...");

      // Setup mock response - new format
      const mockResponse = {
        success: true,
        data: JSON.stringify(mockActiveWindow),
        errorMessage: "",
        requestId: "mock-request-id-active",
      };

      callMcpToolStub.resolves(mockResponse);

      // Call the method
      const windowResponse = await windowManager.getActiveWindow();
      log(`Get Active Window RequestId: ${windowResponse.requestId || "undefined"}`);

      // Verify WindowInfoResult structure
      expect(windowResponse.success).toBe(true);
      expect(windowResponse.requestId).toBeDefined();
      expect(typeof windowResponse.requestId).toBe("string");
      expect(windowResponse.requestId).toBe("mock-request-id-active");
      expect(windowResponse.errorMessage).toBeUndefined();

      // Verify window structure
      expect(windowResponse.window).toBeDefined();
      expect(windowResponse.window?.window_id).toBe(1);
      expect(windowResponse.window?.title).toBe("Test Window 1");
    });

    it("should handle get active window failure", async () => {
      // Use rejects for error simulation
      callMcpToolStub.rejects(new Error("Failed to get active window"));

      const result = await windowManager.getActiveWindow();

      // Verify error result structure
      expect(result.success).toBe(false);
      expect(result.requestId).toBe("");
      expect(result.window).toBeUndefined();
      expect(result.errorMessage).toContain("Failed to get active window");
    });
  });

  describe("activateWindow()", () => {
    it("should activate a window with requestId", async () => {
      log("Testing activateWindow...");

      const windowId = mockWindows[0].window_id;
      log(`Activating window with ID: ${windowId}`);

      // Setup mock response - new format
      const mockResponse = {
        success: true,
        data: "",
        errorMessage: "",
        requestId: "mock-request-id-activate",
      };

      callMcpToolStub.resolves(mockResponse);

      // Call the method
      const activateResponse = await windowManager.activateWindow(windowId);
      log("Window activated successfully");
      log(
        `Activate Window RequestId: ${
          activateResponse.requestId || "undefined"
        }`
      );

      // Verify BoolResult structure
      expect(activateResponse.success).toBe(true);
      expect(activateResponse.requestId).toBeDefined();
      expect(typeof activateResponse.requestId).toBe("string");
      expect(activateResponse.requestId).toBe("mock-request-id-activate");
      expect(activateResponse.errorMessage).toBeUndefined();
    });

    it("should handle activate window failure", async () => {
      // Setup mock to reject
      callMcpToolStub.rejects(new Error("Test error"));

      // Call the method
      const result = await windowManager.activateWindow(1);

      // Verify error result structure
      expect(result.success).toBe(false);
      expect(result.requestId).toBe("");
      expect(result.errorMessage).toContain("Failed to activate window");
    });
  });

  describe("maximizeWindow()", () => {
    it("should maximize a window with requestId", async () => {
      log("Testing maximizeWindow...");

      const windowId = mockWindows[0].window_id;
      log(`Maximizing window with ID: ${windowId}`);

      // Setup mock response - new format
      const mockResponse = {
        success: true,
        data: "",
        errorMessage: "",
        requestId: "mock-request-id-maximize",
      };

      callMcpToolStub.resolves(mockResponse);

      // Call the method
      const maximizeResponse = await windowManager.maximizeWindow(windowId);
      log("Window maximized successfully");
      log(
        `Maximize Window RequestId: ${
          maximizeResponse.requestId || "undefined"
        }`
      );

      // Verify BoolResult structure
      expect(maximizeResponse.success).toBe(true);
      expect(maximizeResponse.requestId).toBeDefined();
      expect(typeof maximizeResponse.requestId).toBe("string");
      expect(maximizeResponse.requestId).toBe("mock-request-id-maximize");
      expect(maximizeResponse.errorMessage).toBeUndefined();
    });
  });

  describe("minimizeWindow()", () => {
    it("should minimize a window with requestId", async () => {
      log("Testing minimizeWindow...");

      const windowId = mockWindows[0].window_id;
      log(`Minimizing window with ID: ${windowId}`);

      // Setup mock response - new format
      const mockResponse = {
        success: true,
        data: "",
        errorMessage: "",
        requestId: "mock-request-id-minimize",
      };

      callMcpToolStub.resolves(mockResponse);

      // Call the method
      const minimizeResponse = await windowManager.minimizeWindow(windowId);
      log("Window minimized successfully");
      log(
        `Minimize Window RequestId: ${
          minimizeResponse.requestId || "undefined"
        }`
      );

      // Verify BoolResult structure
      expect(minimizeResponse.success).toBe(true);
      expect(minimizeResponse.requestId).toBeDefined();
      expect(typeof minimizeResponse.requestId).toBe("string");
      expect(minimizeResponse.requestId).toBe("mock-request-id-minimize");
      expect(minimizeResponse.errorMessage).toBeUndefined();
    });
  });

  describe("restoreWindow()", () => {
    it("should restore a window with requestId", async () => {
      log("Testing restoreWindow...");

      const windowId = mockWindows[0].window_id;
      log(`Restoring window with ID: ${windowId}`);

      // Setup mock response - new format
      const mockResponse = {
        success: true,
        data: "",
        errorMessage: "",
        requestId: "mock-request-id-restore",
      };

      callMcpToolStub.resolves(mockResponse);

      // Call the method
      const restoreResponse = await windowManager.restoreWindow(windowId);
      log("Window restored successfully");
      log(
        `Restore Window RequestId: ${
          restoreResponse.requestId || "undefined"
        }`
      );

      // Verify BoolResult structure
      expect(restoreResponse.success).toBe(true);
      expect(restoreResponse.requestId).toBeDefined();
      expect(typeof restoreResponse.requestId).toBe("string");
      expect(restoreResponse.requestId).toBe("mock-request-id-restore");
      expect(restoreResponse.errorMessage).toBeUndefined();
    });
  });

  describe("resizeWindow()", () => {
    it("should resize a window with requestId", async () => {
      log("Testing resizeWindow...");

      const windowId = mockWindows[0].window_id;
      const width = 800;
      const height = 600;
      log(`Resizing window with ID: ${windowId} to ${width}x${height}`);

      // Setup mock response - new format
      const mockResponse = {
        success: true,
        data: "",
        errorMessage: "",
        requestId: "mock-request-id-resize",
      };

      callMcpToolStub.resolves(mockResponse);

      // Call the method
      const resizeResponse = await windowManager.resizeWindow(windowId, width, height);
      log(`Window resized successfully to ${width}x${height}`);
      log(
        `Resize Window RequestId: ${
          resizeResponse.requestId || "undefined"
        }`
      );

      // Verify BoolResult structure
      expect(resizeResponse.success).toBe(true);
      expect(resizeResponse.requestId).toBeDefined();
      expect(typeof resizeResponse.requestId).toBe("string");
      expect(resizeResponse.requestId).toBe("mock-request-id-resize");
      expect(resizeResponse.errorMessage).toBeUndefined();
    });
  });

  describe("focusMode()", () => {
    it("should enable focus mode with requestId", async () => {
      log("Testing focusMode enable...");

      // Setup mock response - new format
      const mockResponse = {
        success: true,
        data: "",
        errorMessage: "",
        requestId: "mock-request-id-focus-enable",
      };

      callMcpToolStub.resolves(mockResponse);

      // Call the method with focus on
      const focusEnableResponse = await windowManager.focusMode(true);
      log("Focus mode enabled successfully");
      log(
        `Focus Mode Enable RequestId: ${
          focusEnableResponse.requestId || "undefined"
        }`
      );

      // Verify that the response contains requestId
      expect(focusEnableResponse.success).toBe(true);
      expect(focusEnableResponse.requestId).toBeDefined();
      expect(typeof focusEnableResponse.requestId).toBe("string");
      expect(focusEnableResponse.requestId).toBe("mock-request-id-focus-enable");
      expect(focusEnableResponse.errorMessage).toBeUndefined();
    });

    it("should disable focus mode with requestId", async () => {
      log("Testing focusMode disable...");

      // Setup mock response - new format
      const mockResponse = {
        success: true,
        data: "",
        errorMessage: "",
        requestId: "mock-request-id-focus-disable",
      };

      callMcpToolStub.resolves(mockResponse);

      // Call the method with focus off
      const focusDisableResponse = await windowManager.focusMode(false);
      log("Focus mode disabled successfully");
      log(
        `Focus Mode Disable RequestId: ${
          focusDisableResponse.requestId || "undefined"
        }`
      );

      // Verify that the response contains requestId
      expect(focusDisableResponse.success).toBe(true);
      expect(focusDisableResponse.requestId).toBeDefined();
      expect(typeof focusDisableResponse.requestId).toBe("string");
      expect(focusDisableResponse.requestId).toBe("mock-request-id-focus-disable");
      expect(focusDisableResponse.errorMessage).toBeUndefined();
    });
  });
});
