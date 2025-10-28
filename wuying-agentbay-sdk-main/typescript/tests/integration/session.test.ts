import { before } from "node:test";
import { AgentBay, Session } from "../../src";
import { getTestApiKey, extractResourceId } from "../utils/test-helpers";
import { log } from "../../src/utils/logger";

describe("Session", () => {
  describe("properties", () => {
    let agentBay: AgentBay;
    let session: Session;

    beforeEach(async () => {
      const apiKey = getTestApiKey();
      agentBay = new AgentBay({ apiKey });

      // Create a session
      log("Creating a new session for session testing...");
      const createResponse = await agentBay.create();
      session = createResponse.session;
      log(`Session created with ID: ${session.sessionId}`);
      log(
        `Create Session RequestId: ${createResponse.requestId || "undefined"}`
      );
    });

    afterEach(async () => {
      // Clean up the session
      log("Cleaning up: Deleting the session...");
      try {
        if (session) {
          const deleteResponse = await agentBay.delete(session);
          log(
            `Delete Session RequestId: ${
              deleteResponse.requestId || "undefined"
            }`
          );
        }
      } catch (error) {
        log(`Warning: Error deleting session: ${error}`);
      }
    });
    it.only("should have valid sessionId", () => {
      expect(session.sessionId).toBeDefined();
      expect(session.sessionId.length).toBeGreaterThan(0);
    });

    it.only("should have filesystem, command, and ui properties", () => {
      expect(session.fileSystem).toBeDefined();
      expect(session.command).toBeDefined();
      expect(session.ui).toBeDefined();
    });
  });

  describe("methods", () => {
    let agentBay: AgentBay;
    let session: Session;

    beforeEach(async () => {
      const apiKey = getTestApiKey();
      agentBay = new AgentBay({ apiKey });

      // Create a session
      log("Creating a new session for session testing...");
      const createResponse = await agentBay.create({ imageId: "code_latest" });
      session = createResponse.session;
      log(`Session created with ID: ${session.sessionId}`);
      log(
        `Create Session RequestId: ${createResponse.requestId || "undefined"}`
      );
    });

    afterEach(async () => {
      // Clean up the session
      log("Cleaning up: Deleting the session...");
      try {
        if (session) {
          const deleteResponse = await agentBay.delete(session);
          log(
            `Delete Session RequestId: ${
              deleteResponse.requestId || "undefined"
            }`
          );
        }
      } catch (error) {
        log(`Warning: Error deleting session: ${error}`);
      }
    });
    it.only("should return the session ID", () => {
      const sessionId = session.getSessionId();
      expect(sessionId).toBe(session.sessionId);
    });

    it.only("should return the API key", () => {
      const apiKey = session.getAPIKey();
      expect(apiKey).toBe(agentBay.getAPIKey());
    });

    it.only("should return the client", () => {
      const client = session.getClient();
      expect(client).toBeDefined();
    });
  });

  describe("delete", () => {
    let agentBay: AgentBay;
    beforeEach(async () => {
      agentBay = new AgentBay({ apiKey: getTestApiKey() });
    });
    it.only("should delete the session", async () => {
      // Create a new session specifically for this test
      log("Creating a new session for delete testing...");
      const createResponse = await agentBay.create();
      const testSession = createResponse.session;
      log(`Session created with ID: ${testSession.sessionId}`);
      log(
        `Create Session RequestId: ${createResponse.requestId || "undefined"}`
      );

      // Test delete method
      log("Testing session.delete method...");
      try {
        if (testSession) {
          const deleteResponse = await testSession.delete();
          log(
            `Delete Session RequestId: ${
              deleteResponse.requestId || "undefined"
            }`
          );

          // Verify that the response contains requestId
          expect(deleteResponse.requestId).toBeDefined();
          expect(typeof deleteResponse.requestId).toBe("string");

          // Verify the deletion was successful
          expect(deleteResponse.success).toBe(true);
        }
      } catch (error) {
        log(`Note: Session deletion failed: ${error}`);
        // Clean up if the test failed
        try {
          if (testSession) {
            const deleteResponse = await agentBay.delete(testSession);
            log(
              `Cleanup Delete Session RequestId: ${
                deleteResponse.requestId || "undefined"
              }`
            );
          }
        } catch {
          // Ignore cleanup errors
        }
        throw error;
      }
    });
  });

  describe("info", () => {
    let agentBay: AgentBay;
    let session: Session;

    beforeEach(async () => {
      const apiKey = getTestApiKey();
      agentBay = new AgentBay({ apiKey });

      // Create a session
      log("Creating a new session for session testing...");
      const createResponse = await agentBay.create();
      session = createResponse.session;
      log(`Session created with ID: ${session.sessionId}`);
      log(
        `Create Session RequestId: ${createResponse.requestId || "undefined"}`
      );
    });

    afterEach(async () => {
      // Clean up the session
      log("Cleaning up: Deleting the session...");
      try {
        if (session) {
          const deleteResponse = await agentBay.delete(session);
          log(
            `Delete Session RequestId: ${
              deleteResponse.requestId || "undefined"
            }`
          );
        }
      } catch (error) {
        log(`Warning: Error deleting session: ${error}`);
      }
    });
    it.only("should get session info if implemented", async () => {
      // Check if the info method exists
      if (typeof session.info === "function") {
        log("Testing session.info method...");
        try {
          const sessionInfoResponse = await session.info();

          // Verify that the response contains requestId
          expect(sessionInfoResponse.requestId).toBeDefined();
          expect(typeof sessionInfoResponse.requestId).toBe("string");

          // Verify the operation was successful (matching Python test)
          expect(sessionInfoResponse.success).toBe(true);

          // Verify the session info data exists
          expect(sessionInfoResponse.data).toBeDefined();
          const info = sessionInfoResponse.data;

          // Log SessionInfo similar to Python test
          log(`SessionInfo: ${JSON.stringify(info)}`);

          // Check sessionId field (matching Python test)
          expect(info.sessionId).toBeDefined();
          expect(info.sessionId).toBeTruthy();
          expect(info.sessionId).toBe(session.sessionId);

          // Check resourceUrl field (matching Python test)
          expect(info.resourceUrl).toBeDefined();
          expect(info.resourceUrl).toBeTruthy();

          // Check ticket field (matching Python test)
          expect(info).toHaveProperty("ticket");
          // ticket may be empty depending on backend, but should exist

          // Check other fields exist (matching Python test)
          expect(info).toHaveProperty("appId");
          expect(info).toHaveProperty("authCode");
          expect(info).toHaveProperty("connectionProperties");
          expect(info).toHaveProperty("resourceId");
          expect(info).toHaveProperty("resourceType");

          // Log resourceUrl if present
          if (info.resourceUrl) {
            log(`Session ResourceUrl from Info: ${info.resourceUrl}`);

            // Extract resourceId from URL if possible
            const resourceId = extractResourceId(info.resourceUrl);
            if (resourceId) {
              log(`Extracted ResourceId: ${resourceId}`);
            }
          }

          // Log other fields (these may be empty depending on the API response)
          if (info.appId) log(`AppId: ${info.appId}`);
          if (info.authCode) log(`AuthCode: ${info.authCode}`);
          if (info.connectionProperties)
            log(`ConnectionProperties: ${info.connectionProperties}`);
          if (info.resourceId) log(`ResourceId: ${info.resourceId}`);
          if (info.resourceType) log(`ResourceType: ${info.resourceType}`);
          if (info.ticket) log(`Ticket: ${info.ticket}`);

          log(
            `Session Info RequestId: ${
              sessionInfoResponse.requestId || "undefined"
            }`
          );
        } catch (error) {
          log(`Note: Session info retrieval failed: ${error}`);
          // Don't fail the test if info method is not fully implemented
          throw error;
        }
      } else {
        log("Note: Session info method is not available, skipping info test");
      }
    });
  });
});
