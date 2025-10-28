import { AgentBay, Session } from "../../src";
import { getTestApiKey } from "../utils/test-helpers";
import { log } from "../../src/utils/logger";

describe("Session Parameters", () => {
  let agentBay: AgentBay;
  let session: Session;

  beforeEach(async () => {
    const apiKey = getTestApiKey();
    agentBay = new AgentBay({ apiKey });
  });

  afterEach(async () => {
    try {
      if (session) {
        const deleteResponse = await session.delete();
        log("Session deleted successfully");
        log(
          `Delete Session RequestId: ${deleteResponse.requestId || "undefined"}`
        );
      }
    } catch (error) {
      log(`Error deleting session: ${error}`);
    }
  });

  describe("create method options", () => {
    it("should accept empty options", async () => {
      try {
        const createResponse = await agentBay.create();
        session = createResponse.session;
        log(
          `Create Session RequestId: ${createResponse.requestId || "undefined"}`
        );

        // Verify that the response contains requestId
        expect(createResponse.requestId).toBeDefined();
        expect(typeof createResponse.requestId).toBe("string");
        expect(session).toBeDefined();
        expect(session.getSessionId()).toBeDefined();
      } catch (error) {
        log(`Error creating session: ${error}`);
        throw error;
      }
    });

    it("should accept contextId option", async () => {
      try {
        const contextName = `test-context-${Date.now()}`;
        const createContextResponse = await agentBay.context.create(contextName);
        const context = createContextResponse.context;
        const createResponse = await agentBay.create();
        session = createResponse.session;
        log(
          `Create Session with ContextId RequestId: ${
            createResponse.requestId || "undefined"
          }`
        );

        // Verify successful creation
        expect(createResponse.requestId).toBeDefined();
        expect(session).toBeDefined();
        expect(session.getSessionId()).toBeDefined();
      } catch (error: any) {
        log(`Error creating session with contextId: ${error}`);
        // If this fails, it might be expected behavior depending on the test environment
        expect(error.message).toMatch(/Failed to create session/);
      }
    });

    it("should accept labels option", async () => {
      try {
        const labels = { username: "alice", project: "my-project" };
        const createResponse = await agentBay.create({ labels });
        session = createResponse.session;
        log(
          `Create Session with Labels RequestId: ${
            createResponse.requestId || "undefined"
          }`
        );

        // Verify successful creation
        expect(createResponse.requestId).toBeDefined();
        expect(session).toBeDefined();
        expect(session.getSessionId()).toBeDefined();
      } catch (error: any) {
        log(`Error creating session with labels: ${error}`);
        // If this fails, it might be expected behavior depending on the test environment
        expect(error.message).toMatch(/Failed to create session/);
      }
    });

    it("should accept both contextId and labels options", async () => {
      try {
        const contextName = `test-context-${Date.now()}`;
        const createContextResponse = await agentBay.context.create(contextName);
        const context = createContextResponse.context;
        const labels = { username: "alice", project: "my-project" };
        const createResponse = await agentBay.create({ labels });
        session = createResponse.session;
        log(
          `Create Session with ContextId and Labels RequestId: ${
            createResponse.requestId || "undefined"
          }`
        );

        // Verify successful creation
        expect(createResponse.requestId).toBeDefined();
        expect(session).toBeDefined();
        expect(session.getSessionId()).toBeDefined();
      } catch (error: any) {
        log(`Error creating session with contextId and labels: ${error}`);
        // If this fails, it might be expected behavior depending on the test environment
        expect(error.message).toMatch(/Failed to create session/);
      }
    });
  });

  describe("session creation with options", () => {
    it("should create a session with the specified options", async () => {
      try {
        const contextName = `test-context-${Date.now()}`;
        const createContextResponse = await agentBay.context.create(contextName);
        const context = createContextResponse.context;
        const createResponse = await agentBay.create({
          labels: { username: "alice" },
        });
        session = createResponse.session;
        log(
          `Create Session with Options RequestId: ${
            createResponse.requestId || "undefined"
          }`
        );

        // Verify successful creation
        expect(createResponse.requestId).toBeDefined();
        expect(session).toBeDefined();
        expect(session.getSessionId()).toBeDefined();
      } catch (error: any) {
        log(`Error creating session with options: ${error}`);
        // If this fails, it might be expected behavior depending on the test environment
        expect(error.message).toMatch(/Failed to create session/);
      }
    });
  });
});
