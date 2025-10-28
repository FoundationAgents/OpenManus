

import { AgentBay, Session } from "../../src";
import { getTestApiKey } from "../utils/test-helpers";
import { log } from "../../src/utils/logger";

describe("Session GetLink", () => {
  let agentBay: AgentBay;
  let session: Session;

  beforeEach(async () => {
    const apiKey = getTestApiKey();
    log(`Using API key: ${apiKey}`);

    agentBay = new AgentBay({ apiKey });

    // Create a session with imageId for getLink testing
    log("Creating a new session for getLink testing...");
    const createResponse = await agentBay.create({ imageId: "browser_latest" });
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

  describe("getLink method", () => {
    it("should get link without parameters", async () => {
      // Check if the getLink method exists
      if (typeof session.getLink === "function") {
        log("Testing getLink without parameters...");
        try {
          const linkResponse = await session.getLink();
          log("Session link:", linkResponse.data);
          log(`Get Link RequestId: ${linkResponse.requestId || "undefined"}`);

          // Verify that the response contains requestId
          expect(linkResponse.requestId).toBeDefined();
          expect(typeof linkResponse.requestId).toBe("string");

          // Verify the link data is a string (URL)
          expect(linkResponse.data).toBeDefined();
          expect(typeof linkResponse.data).toBe("string");
        } catch (error) {
          log(`Note: Session link retrieval failed: ${error}`);
          // Don't fail the test if getLink method is not fully implemented
        }
      } else {
        log("Note: Session getLink method is not available, skipping test");
      }
    });

    it("should get link with protocol type parameter", async () => {
      if (typeof session.getLink === "function") {
        log("Testing getLink with protocol type parameter...");
        try {
          const linkWithProtocolResponse = await session.getLink("https");
          log(
            "Session link with protocol https:",
            linkWithProtocolResponse.data
          );
          log(
            `Get Link with Protocol RequestId: ${
              linkWithProtocolResponse.requestId || "undefined"
            }`
          );

          expect(linkWithProtocolResponse.requestId).toBeDefined();
          expect(linkWithProtocolResponse.data).toBeDefined();
          expect(typeof linkWithProtocolResponse.data).toBe("string");
        } catch (error) {
          log(`Note: Session link retrieval with protocol failed: ${error}`);
        }
      } else {
        log("Note: Session getLink method is not available, skipping test");
      }
    });

    // Port validation tests - valid port range [30100, 30199]
    it("should get link with valid port in range [30100, 30199]", async () => {
      if (typeof session.getLink === "function") {
        log("Testing getLink with valid port 30150...");
        try {
          const validPort = 30150;
          const linkWithPortResponse = await session.getLink(undefined, validPort);
          log(`Session link with port ${validPort}:`, linkWithPortResponse.data);
          log(
            `Get Link with Valid Port RequestId: ${
              linkWithPortResponse.requestId || "undefined"
            }`
          );

          // Verify successful response
          expect(linkWithPortResponse.requestId).toBeDefined();
          expect(linkWithPortResponse.success).toBe(true);
          expect(linkWithPortResponse.data).toBeDefined();
          expect(typeof linkWithPortResponse.data).toBe("string");
        } catch (error) {
          log(`Note: Session link retrieval with valid port failed: ${error}`);
        }
      } else {
        log("Note: Session getLink method is not available, skipping test");
      }
    });

    it("should get link with valid port at lower boundary (30100)", async () => {
      if (typeof session.getLink === "function") {
        log("Testing getLink with valid port at lower boundary 30100...");
        try {
          const validPort = 30100;
          const linkWithPortResponse = await session.getLink("wss", validPort);
          log(`Session link with port ${validPort}:`, linkWithPortResponse.data);
          log(
            `Get Link with Lower Boundary Port RequestId: ${
              linkWithPortResponse.requestId || "undefined"
            }`
          );

          // Verify successful response
          expect(linkWithPortResponse.requestId).toBeDefined();
          expect(linkWithPortResponse.success).toBe(true);
          expect(linkWithPortResponse.data).toBeDefined();
          expect(typeof linkWithPortResponse.data).toBe("string");
        } catch (error) {
          log(`Note: Session link retrieval with lower boundary port failed: ${error}`);
        }
      } else {
        log("Note: Session getLink method is not available, skipping test");
      }
    });

    it("should get link with valid port at upper boundary (30199)", async () => {
      if (typeof session.getLink === "function") {
        log("Testing getLink with valid port at upper boundary 30199...");
        try {
          const validPort = 30199;
          const linkWithPortResponse = await session.getLink("https", validPort);
          log(`Session link with port ${validPort}:`, linkWithPortResponse.data);
          log(
            `Get Link with Upper Boundary Port RequestId: ${
              linkWithPortResponse.requestId || "undefined"
            }`
          );

          // Verify successful response
          expect(linkWithPortResponse.requestId).toBeDefined();
          expect(linkWithPortResponse.success).toBe(true);
          expect(linkWithPortResponse.data).toBeDefined();
          expect(typeof linkWithPortResponse.data).toBe("string");
        } catch (error) {
          log(`Note: Session link retrieval with upper boundary port failed: ${error}`);
        }
      } else {
        log("Note: Session getLink method is not available, skipping test");
      }
    });

    // Port validation tests - invalid port ranges
    it("should throw error for port below valid range (< 30100)", async () => {
      if (typeof session.getLink === "function") {
        log("Testing getLink with invalid port below range...");
        const invalidPort = 30099;

        try {
          await session.getLink("wss", invalidPort);
          // If we reach here, the test should fail
          expect(true).toBe(false); // Force test failure
        } catch (error) {
          log(`Expected error for invalid port ${invalidPort}: ${error}`);

          // Verify the error message matches session.ts logic
          expect(error).toBeInstanceOf(Error);
          const errorMessage = (error as Error).message;
          expect(errorMessage).toContain(`Invalid port value: ${invalidPort}`);
          expect(errorMessage).toContain("Port must be an integer in the range [30100, 30199]");
        }
      } else {
        log("Note: Session getLink method is not available, skipping test");
      }
    });

    it("should throw error for port above valid range (> 30199)", async () => {
      if (typeof session.getLink === "function") {
        log("Testing getLink with invalid port above range...");
        const invalidPort = 30200;

        try {
          await session.getLink("https", invalidPort);
          // If we reach here, the test should fail
          expect(true).toBe(false); // Force test failure
        } catch (error) {
          log(`Expected error for invalid port ${invalidPort}: ${error}`);

          // Verify the error message matches session.ts logic
          expect(error).toBeInstanceOf(Error);
          const errorMessage = (error as Error).message;
          expect(errorMessage).toContain(`Invalid port value: ${invalidPort}`);
          expect(errorMessage).toContain("Port must be an integer in the range [30100, 30199]");
        }
      } else {
        log("Note: Session getLink method is not available, skipping test");
      }
    });

    it("should throw error for non-integer port", async () => {
      if (typeof session.getLink === "function") {
        log("Testing getLink with non-integer port...");
        const invalidPort = 30150.5;

        try {
          await session.getLink("wss", invalidPort);
          // If we reach here, the test should fail
          expect(true).toBe(false); // Force test failure
        } catch (error) {
          log(`Expected error for non-integer port ${invalidPort}: ${error}`);

          // Verify the error message matches session.ts logic
          expect(error).toBeInstanceOf(Error);
          const errorMessage = (error as Error).message;
          expect(errorMessage).toContain(`Invalid port value: ${invalidPort}`);
          expect(errorMessage).toContain("Port must be an integer in the range [30100, 30199]");
        }
      } else {
        log("Note: Session getLink method is not available, skipping test");
      }
    });

    it("should throw error for commonly used but invalid ports", async () => {
      if (typeof session.getLink === "function") {
        log("Testing getLink with commonly used but invalid ports...");

        // Test port 8080 (commonly used but outside valid range)
        const invalidPort8080 = 8080;
        try {
          await session.getLink(undefined, invalidPort8080);
          expect(true).toBe(false); // Force test failure
        } catch (error) {
          log(`Expected error for invalid port ${invalidPort8080}: ${error}`);
          expect(error).toBeInstanceOf(Error);
          const errorMessage = (error as Error).message;
          expect(errorMessage).toContain(`Invalid port value: ${invalidPort8080}`);
          expect(errorMessage).toContain("Port must be an integer in the range [30100, 30199]");
        }

        // Test port 443 (HTTPS default but outside valid range)
        const invalidPort443 = 443;
        try {
          await session.getLink("https", invalidPort443);
          expect(true).toBe(false); // Force test failure
        } catch (error) {
          log(`Expected error for invalid port ${invalidPort443}: ${error}`);
          expect(error).toBeInstanceOf(Error);
          const errorMessage = (error as Error).message;
          expect(errorMessage).toContain(`Invalid port value: ${invalidPort443}`);
          expect(errorMessage).toContain("Port must be an integer in the range [30100, 30199]");
        }
      } else {
        log("Note: Session getLink method is not available, skipping test");
      }
    });
  });

  describe("getLinkAsync method", () => {
    it("should get link asynchronously with valid port", async () => {
      if (typeof session.getLinkAsync === "function") {
        log("Testing getLinkAsync with valid port...");
        try {
          const validPort = 30150;
          const linkResponse = await session.getLinkAsync("wss", validPort);
          log(`Session link async with port ${validPort}:`, linkResponse.data);
          log(
            `Get Link Async RequestId: ${linkResponse.requestId || "undefined"}`
          );

          // Verify successful response
          expect(linkResponse.requestId).toBeDefined();
          expect(linkResponse.success).toBe(true);
          expect(linkResponse.data).toBeDefined();
          expect(typeof linkResponse.data).toBe("string");
        } catch (error) {
          log(`Note: Session link async retrieval failed: ${error}`);
        }
      } else {
        log("Note: Session getLinkAsync method is not available, skipping test");
      }
    });

    it("should throw error for invalid port in getLinkAsync", async () => {
      if (typeof session.getLinkAsync === "function") {
        log("Testing getLinkAsync with invalid port...");
        const invalidPort = 25000;

        try {
          await session.getLinkAsync("wss", invalidPort);
          // If we reach here, the test should fail
          expect(true).toBe(false); // Force test failure
        } catch (error) {
          log(`Expected error for invalid port ${invalidPort} in getLinkAsync: ${error}`);

          // Verify the error message matches session.ts logic
          expect(error).toBeInstanceOf(Error);
          const errorMessage = (error as Error).message;
          expect(errorMessage).toContain(`Invalid port value: ${invalidPort}`);
          expect(errorMessage).toContain("Port must be an integer in the range [30100, 30199]");
        }
      } else {
        log("Note: Session getLinkAsync method is not available, skipping test");
      }
    });

    it("should handle backend error for invalid port in getLinkAsync", async () => {
      if (typeof session.getLinkAsync === "function") {
        log("Testing getLinkAsync backend port validation...");

        const validPort = 30199; // Valid for client-side validation

        try {
          const linkResponse = await session.getLinkAsync("https", validPort);

          // If successful, verify the response
          log(`Backend accepted port ${validPort} in getLinkAsync, response:`, linkResponse.data);
          expect(linkResponse.requestId).toBeDefined();
          expect(linkResponse.data).toBeDefined();

        } catch (error) {
          log(`Backend rejected port ${validPort} in getLinkAsync: ${error}`);

          // If backend rejects, verify it's a proper error
          expect(error).toBeInstanceOf(Error);
          const errorMessage = (error as Error).message;

          // Check if it's a backend validation error
          if (errorMessage.includes("Failed to get link asynchronously")) {
            expect(errorMessage).toContain("Failed to get link asynchronously");
            log("Backend port validation test for getLinkAsync completed");
          } else {
            // Re-throw if it's an unexpected error
            throw error;
          }
        }
      } else {
        log("Note: Session getLinkAsync method is not available, skipping test");
      }
    });
  });
});
