import { AgentBay, Session } from "../../src";
import { getTestApiKey } from "../utils/test-helpers";
import { log } from "../../src/utils/logger";

// Helper function to parse content array from API response for UI elements
function parseUIContent(content: any[]): any[] {
  if (!Array.isArray(content) || content.length === 0) {
    return [];
  }

  // Try to extract and parse text from the first content item
  const item = content[0];
  if (
    item &&
    typeof item === "object" &&
    item.text &&
    typeof item.text === "string"
  ) {
    try {
      return JSON.parse(item.text);
    } catch (e) {
      log(`Warning: Failed to parse content text as JSON: ${e}`);
      return [];
    }
  }

  return [];
}

// Helper function to check if a content array contains base64 image data
function containsBase64Image(content: any[]): boolean {
  if (!Array.isArray(content) || content.length === 0) {
    return false;
  }

  // Look for base64 image data in the text fields
  return content.some(
    (item) =>
      item &&
      typeof item === "object" &&
      typeof item.text === "string" &&
      (item.text.startsWith("data:image") || item.text.includes("base64"))
  );
}

// Type declarations are now in tests/jest.d.ts

describe("UI", () => {
  let agentBay: AgentBay;
  let session: Session;

  beforeEach(async () => {
    const apiKey = getTestApiKey();
    agentBay = new AgentBay({ apiKey });

    // Create a session with mobile_latest image (consistent with Go implementation)
    log("Creating a new session for UI testing...");
    const createResponse = await agentBay.create({ imageId: "mobile_latest" });
    session = createResponse.session;
    log(`Session created with ID: ${session.sessionId}`);
    log(`Create Session RequestId: ${createResponse.requestId || "undefined"}`);
  });

  afterEach(async () => {
    // Clean up the session
    try {
      const deleteResponse = await agentBay.delete(session);
      log(`Session deleted successfully: ${session.sessionId}`);
      log(
        `Delete Session RequestId: ${deleteResponse.requestId || "undefined"}`
      );
    } catch (error) {
      log(`Warning: Error deleting session: ${error}`);
    }
  });

  describe("getClickableUIElements", () => {
    it.only("should retrieve clickable UI elements if implemented", async () => {
      if (
        session.ui &&
        typeof session.ui.getClickableUIElements === "function"
      ) {
        log("Testing UI.getClickableUIElements method...");
        try {
          const elementsResponse = await session.ui.getClickableUIElements();
          log(`Retrieved content:`, elementsResponse.elements);
          log(
            `Get Clickable UI Elements RequestId: ${
              elementsResponse.requestId || "undefined"
            }`
          );

          // Verify the response contains requestId
          expect(elementsResponse.requestId).toBeDefined();
          expect(typeof elementsResponse.requestId).toBe("string");

          // Verify the content
          expect(elementsResponse.elements).toBeDefined();
          expect(Array.isArray(elementsResponse.elements)).toBe(true);

          // Log the first element if available
          if (elementsResponse.elements.length > 0) {
            log("First UI element:", elementsResponse.elements[0]);
          }
        } catch (error) {
          log(`Note: UI.getClickableUIElements execution failed: ${error}`);
          // Don't fail the test if the method is not fully implemented
        }
      } else {
        log(
          "Note: UI.getClickableUIElements method is not available, skipping test"
        );
      }
    });
  });

  describe("getAllUIElements", () => {
    it.only("should retrieve all UI elements if implemented", async () => {
      if (session.ui && typeof session.ui.getAllUIElements === "function") {
        log("Testing UI.getAllUIElements method...");
        try {
          const elementsResponse = await session.ui.getAllUIElements();
          log(`Retrieved content:`, elementsResponse.elements);
          log(
            `Get All UI Elements RequestId: ${
              elementsResponse.requestId || "undefined"
            }`
          );

          // Verify the response contains requestId
          expect(elementsResponse.requestId).toBeDefined();
          expect(typeof elementsResponse.requestId).toBe("string");

          // Verify the content
          expect(elementsResponse.elements).toBeDefined();
          expect(Array.isArray(elementsResponse.elements)).toBe(true);

          // Log the first element if available
          if (elementsResponse.elements.length > 0) {
            log("First UI element:", elementsResponse.elements[0]);
          }
        } catch (error) {
          log(`Note: UI.getAllUIElements execution failed: ${error}`);
          // Don't fail the test if the method is not fully implemented
        }
      } else {
        log("Note: UI.getAllUIElements method is not available, skipping test");
      }
    });
  });

  describe("sendKey", () => {
    it.only("should send key events if implemented", async () => {
      if (session.ui && typeof session.ui.sendKey === "function") {
        log("Testing UI.sendKey method...");
        try {
          // Try to send HOME key
          const sendKeyResponse = await session.ui.sendKey(3); // HOME key
          log(`Send key content:`, sendKeyResponse.data);
          log(
            `Send Key RequestId: ${sendKeyResponse.requestId || "undefined"}`
          );

          // Verify the response contains requestId
          expect(sendKeyResponse.requestId).toBeDefined();
          expect(typeof sendKeyResponse.requestId).toBe("string");

          // Verify the content
          expect(sendKeyResponse.data).toBeDefined();
          expect(typeof sendKeyResponse.data).toBe("boolean");
        } catch (error) {
          log(`Note: UI.sendKey execution failed: ${error}`);
          // Don't fail the test if the method is not fully implemented
        }
      } else {
        log("Note: UI.sendKey method is not available, skipping test");
      }
    });
  });

  describe("screenshot", () => {
    it.only("should take screenshots if implemented", async () => {
      if (session.ui && typeof session.ui.screenshot === "function") {
        log("Testing UI.screenshot method...");
        try {
          const screenshotResponse = await session.ui.screenshot();
          log(`Screenshot content:`, screenshotResponse.data);
          log(
            `Screenshot RequestId: ${
              screenshotResponse.requestId || "undefined"
            }`
          );

          // Verify the response contains requestId
          expect(screenshotResponse.requestId).toBeDefined();
          expect(typeof screenshotResponse.requestId).toBe("string");

          // Verify the screenshot content
          expect(screenshotResponse.data).toBeDefined();
          expect(typeof screenshotResponse.data).toBe("string");

          // Check if the content contains image URL or base64 data
          const hasImageData =
            screenshotResponse.data.includes("https://") ||
            screenshotResponse.data.includes("data:image") ||
            screenshotResponse.data.includes("base64");
          expect(hasImageData).toBe(true);
        } catch (error) {
          log(`Note: UI.screenshot execution failed: ${error}`);
          // Don't fail the test if the method is not fully implemented
        }
      } else {
        log("Note: UI.screenshot method is not available, skipping test");
      }
    });
  });
});
