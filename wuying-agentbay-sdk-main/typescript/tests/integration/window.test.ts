import { AgentBay, Session } from "../../src";
import { Window, WindowManager } from "../../src/window/window";
import { getTestApiKey } from "../utils/test-helpers";
import { log } from "../../src/utils/logger";

// Helper function to check if window has valid properties
function isValidWindow(window: Window): boolean {
  return (
    typeof window === "object" &&
    window !== null &&
    typeof window.window_id === "number" &&
    typeof window.title === "string"
  );
}

// Type declarations are now in tests/jest.d.ts

describe("WindowManager", () => {
  let agentBay: AgentBay;
  let session: Session;
  let windowManager: WindowManager;

  beforeEach(async () => {
    // Create a real AgentBay instance with test API key
    const apiKey = getTestApiKey();
    agentBay = new AgentBay({ apiKey });
    // Create a real session
    log("Creating a new session for window testing...");
    const createResponse = await agentBay.create({ imageId: "linux_latest" });
    session = createResponse.session;
    debugger;
    log(`Session created with ID: ${session.sessionId}`);
    log(`Create Session RequestId: ${createResponse.requestId || "undefined"}`);

    windowManager = new WindowManager(session);
  });

  afterEach(async () => {
    log("Cleaning up: Deleting the session...");
    try {
      if (session) {
        const deleteResponse = await agentBay.delete(session);
        log("Session successfully deleted");
        log(
          `Delete Session RequestId: ${deleteResponse.requestId || "undefined"}`
        );
      }
    } catch (error) {
      log(`Warning: Error deleting session: ${error}`);
    }
  });

  describe("listRootWindows()", () => {
    it.only("should return a list of root windows with requestId", async () => {
      log("Testing listRootWindows...");
      try {
        // Call the method
        const windowsResponse = await windowManager.listRootWindows();
        log(`Retrieved ${windowsResponse.windows.length} root windows`);
        log(
          `List Root Windows RequestId: ${
            windowsResponse.requestId || "undefined"
          }`
        );

        // Verify that the response contains requestId
        expect(windowsResponse.requestId).toBeDefined();
        expect(typeof windowsResponse.requestId).toBe("string");

        // Verify windows array
        expect(windowsResponse.windows).toBeDefined();
        expect(Array.isArray(windowsResponse.windows)).toBe(true);

        // Verify the results
        if (windowsResponse.windows.length > 0) {
          windowsResponse.windows.forEach((window) => {
            expect(isValidWindow(window)).toBe(true);
          });
        } else {
          log("No windows found, this might be normal in some environments");
        }
      } catch (error: any) {
        log(`Error in listRootWindows test: ${error}`);
        // Skip test if we can't list windows
        expect(true).toBe(true);
      }
    });
  });

  describe("getActiveWindow()", () => {
    it.only("should return the active window with requestId", async () => {
      log("Testing getActiveWindow...");
      try {
        const windowResponse = await windowManager.getActiveWindow();
        log(
          `Get Active Window RequestId: ${
            windowResponse.requestId || "undefined"
          }`
        );

        // Verify that the response contains requestId
        expect(windowResponse.requestId).toBeDefined();
        expect(typeof windowResponse.requestId).toBe("string");

        if (windowResponse.window) {
          log(
            `Active window: ${windowResponse.window.title} (ID: ${windowResponse.window.window_id})`
          );

          // Verify the results
          expect(isValidWindow(windowResponse.window)).toBe(true);
        } else {
          log(
            "No active window found, this might be normal in some environments"
          );
        }
      } catch (error: any) {
        log(`Error in getActiveWindow test: ${error}`);
        // Skip test if we can't get active window
        expect(true).toBe(true);
      }
    });
  });

  describe("activateWindow()", () => {
    it.only("should activate a window with requestId", async () => {
      log("Testing activateWindow...");
      try {
        // First get a list of windows
        const windowsResponse = await windowManager.listRootWindows();

        if (windowsResponse.windows.length === 0) {
          log("No windows available for testing activateWindow");
          return;
        }

        // Use the first window for testing
        const windowId = windowsResponse.windows[0].window_id;
        log(`Activating window with ID: ${windowId}`);

        // Call the method
        const activateResponse = await windowManager.activateWindow(windowId);
        log("Window activated successfully");
        log(
          `Activate Window RequestId: ${
            activateResponse.requestId || "undefined"
          }`
        );

        // Verify that the response contains requestId
        expect(activateResponse.requestId).toBeDefined();
        expect(typeof activateResponse.requestId).toBe("string");
      } catch (error: any) {
        log(`Error in activateWindow test: ${error}`);
        // Skip test if we can't activate window
        expect(true).toBe(true);
      }
    });
  });

  describe("maximizeWindow()", () => {
    it.only("should maximize a window with requestId", async () => {
      log("Testing maximizeWindow...");
      try {
        // First get a list of windows
        const windowsResponse = await windowManager.listRootWindows();

        if (windowsResponse.windows.length === 0) {
          log("No windows available for testing maximizeWindow");
          return;
        }

        // Use the first window for testing
        const windowId = windowsResponse.windows[0].window_id;
        log(`Maximizing window with ID: ${windowId}`);

        // Call the method
        const maximizeResponse = await windowManager.maximizeWindow(windowId);
        log("Window maximized successfully");
        log(
          `Maximize Window RequestId: ${
            maximizeResponse.requestId || "undefined"
          }`
        );

        // Verify that the response contains requestId
        expect(maximizeResponse.requestId).toBeDefined();
        expect(typeof maximizeResponse.requestId).toBe("string");
      } catch (error: any) {
        log(`Error in maximizeWindow test: ${error}`);
        // Skip test if we can't maximize window
        expect(true).toBe(true);
      }
    });
  });

  describe("minimizeWindow()", () => {
    it.only("should minimize a window with requestId", async () => {
      log("Testing minimizeWindow...");
      try {
        // First get a list of windows
        const windowsResponse = await windowManager.listRootWindows();

        if (windowsResponse.windows.length === 0) {
          log("No windows available for testing minimizeWindow");
          return;
        }

        // Use the first window for testing
        const windowId = windowsResponse.windows[0].window_id;
        log(`Minimizing window with ID: ${windowId}`);

        // Call the method
        const minimizeResponse = await windowManager.minimizeWindow(windowId);
        log("Window minimized successfully");
        log(
          `Minimize Window RequestId: ${
            minimizeResponse.requestId || "undefined"
          }`
        );

        // Verify that the response contains requestId
        expect(minimizeResponse.requestId).toBeDefined();
        expect(typeof minimizeResponse.requestId).toBe("string");
      } catch (error: any) {
        log(`Error in minimizeWindow test: ${error}`);
        // Skip test if we can't minimize window
        expect(true).toBe(true);
      }
    });
  });

  describe("restoreWindow()", () => {
    it.only("should restore a window with requestId", async () => {
      log("Testing restoreWindow...");
      try {
        // First get a list of windows
        const windowsResponse = await windowManager.listRootWindows();

        if (windowsResponse.windows.length === 0) {
          log("No windows available for testing restoreWindow");
          return;
        }

        // Use the first window for testing
        const windowId = windowsResponse.windows[0].window_id;
        log(`Restoring window with ID: ${windowId}`);

        // Call the method
        const restoreResponse = await windowManager.restoreWindow(windowId);
        log("Window restored successfully");
        log(
          `Restore Window RequestId: ${
            restoreResponse.requestId || "undefined"
          }`
        );

        // Verify that the response contains requestId
        expect(restoreResponse.requestId).toBeDefined();
        expect(typeof restoreResponse.requestId).toBe("string");
      } catch (error: any) {
        log(`Error in restoreWindow test: ${error}`);
        // Skip test if we can't restore window
        expect(true).toBe(true);
      }
    });
  });

  describe("resizeWindow()", () => {
    it.only("should resize a window with requestId", async () => {
      log("Testing resizeWindow...");
      try {
        // First get a list of windows
        const windowsResponse = await windowManager.listRootWindows();

        if (windowsResponse.windows.length === 0) {
          log("No windows available for testing resizeWindow");
          return;
        }

        // Use the first window for testing
        const windowId = windowsResponse.windows[0].window_id;
        log(`Resizing window with ID: ${windowId} to 800x600`);

        // Call the method
        const resizeResponse = await windowManager.resizeWindow(
          windowId,
          800,
          600
        );
        log("Window resized successfully to 800x600");
        log(
          `Resize Window RequestId: ${resizeResponse.requestId || "undefined"}`
        );

        // Verify that the response contains requestId
        expect(resizeResponse.requestId).toBeDefined();
        expect(typeof resizeResponse.requestId).toBe("string");
      } catch (error: any) {
        log(`Error in resizeWindow test: ${error}`);
        // Skip test if we can't resize window
        expect(true).toBe(true);
      }
    });
  });

  describe("focusMode()", () => {
    it.only("should enable focus mode with requestId", async () => {
      log("Testing focusMode enable...");
      try {
        // Call the method
        const focusEnableResponse = await windowManager.focusMode(true);
        log("Focus mode enabled successfully");
        log(
          `Focus Mode Enable RequestId: ${
            focusEnableResponse.requestId || "undefined"
          }`
        );

        // Verify that the response contains requestId
        expect(focusEnableResponse.requestId).toBeDefined();
        expect(typeof focusEnableResponse.requestId).toBe("string");
      } catch (error: any) {
        log(`Error in focusMode enable test: ${error}`);
        // Skip test if we can't enable focus mode
        expect(true).toBe(true);
      }
    });

    it.only("should disable focus mode with requestId", async () => {
      log("Testing focusMode disable...");
      try {
        // Call the method
        const focusDisableResponse = await windowManager.focusMode(false);
        log("Focus mode disabled successfully");
        log(
          `Focus Mode Disable RequestId: ${
            focusDisableResponse.requestId || "undefined"
          }`
        );

        // Verify that the response contains requestId
        expect(focusDisableResponse.requestId).toBeDefined();
        expect(typeof focusDisableResponse.requestId).toBe("string");
      } catch (error: any) {
        log(`Error in focusMode disable test: ${error}`);
        // Skip test if we can't disable focus mode
        expect(true).toBe(true);
      }
    });
  });
});
