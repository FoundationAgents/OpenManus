import { AgentBay, Session, CreateSessionParams, ContextSync } from "../../src";
import { getTestApiKey } from "../utils/test-helpers";
import { log } from "../../src/utils/logger";

// Helper to conditionally run tests
const itif = it;

// Helper to generate a unique ID
function generateUniqueId(): string {
  return Math.random().toString(36).substring(2, 10);
}

describe("SessionDeleteIntegration", () => {
  let agentBay: AgentBay;

  beforeAll(() => {
    const apiKey = getTestApiKey();
    agentBay = new AgentBay({ apiKey });
  });

  itif("should delete session without parameters", async () => {
    // Create a new session
    log("Creating a new session for delete testing...");
    const createResponse = await agentBay.create();
    expect(createResponse.success).toBe(true);

    const session = createResponse.session;
    log(`Session created with ID: ${session.sessionId}`);

    // Delete session without parameters
    log("Deleting session without parameters...");
    const deleteResult = await session.delete();
    expect(deleteResult.success).toBe(true);
    log(`Session deleted (RequestId: ${deleteResult.requestId || "undefined"})`);

    // Verify the session was deleted
    const listResult = await agentBay.listByLabels();
    expect(listResult.success).toBe(true);
    
    // Check that our session is not in the list
    const sessions = listResult.data || [];
    for (const s of sessions) {
      expect(s.sessionId).not.toBe(session.sessionId);
    }
  });

  itif("should delete session with syncContext=true", async () => {
    try {
      // Create a context
      const contextName = `test-context-${generateUniqueId()}`;
      log(`Creating context: ${contextName}...`);
      const contextResult = await agentBay.context.create(contextName);
      expect(contextResult.contextId).toBeDefined();
      expect(contextResult.contextId.length).toBeGreaterThan(0);
      
      const contextId = contextResult.contextId;
      log(`Context created with ID: ${contextId}`);

      // Create persistence configuration
      const persistenceData = [
        {
          contextId: contextId,
          path: "/home/wuying/test"
        } as ContextSync
      ];

      // Create a session with context
      const params: CreateSessionParams = {
        imageId: "linux_latest",
        contextSync: persistenceData
      };

      log("Creating a session with context...");
      const createResponse = await agentBay.create(params);
      expect(createResponse.success).toBe(true);

      const session = createResponse.session;
      log(`Session created with ID: ${session.sessionId}`);

      // Create a test file in the session
      try {
        const testCmd = "echo 'test file content' > /home/wuying/test/testfile.txt";
        const cmdResult = await session.command.executeCommand(testCmd);
        log(`Created test file: ${cmdResult}`);
      } catch (error) {
        log(`Warning: Failed to create test file: ${error}`);
      }

      // Delete session with syncContext=true
      log("Deleting session with syncContext=true...");
      const deleteResult = await session.delete(true);
      expect(deleteResult.success).toBe(true);
      log(`Session deleted with syncContext=true (RequestId: ${deleteResult.requestId || "undefined"})`);

      // Verify the session was deleted
      const listResult = await agentBay.listByLabels();
      expect(listResult.success).toBe(true);
      
      // Check that our session is not in the list
      const sessions = listResult.data || [];
      for (const s of sessions) {
        expect(s.sessionId).not.toBe(session.sessionId);
      }

      // Clean up context
      try {
        const getContextResult = await agentBay.context.get(contextName);
        if (getContextResult.context) {
          const deleteContextResult = await agentBay.context.delete(getContextResult.context);
          log(`Context ${contextId} deleted (Success: ${deleteContextResult.success})`);
        }
      } catch (error) {
        log(`Warning: Failed to clean up context: ${error}`);
      }
    } catch (error) {
      fail(`Test failed with error: ${error}`);
    }
  });

  itif("should delete session using AgentBay.delete with syncContext=true", async () => {
    try {
      // Create a context
      const contextName = `test-context-${generateUniqueId()}`;
      log(`Creating context: ${contextName}...`);
      const contextResult = await agentBay.context.create(contextName);
      expect(contextResult.contextId).toBeDefined();
      expect(contextResult.contextId.length).toBeGreaterThan(0);
      
      const contextId = contextResult.contextId;
      log(`Context created with ID: ${contextId}`);

      // Create persistence configuration
      const persistenceData = [
        {
          contextId: contextId,
          path: "/home/wuying/test2"
        } as ContextSync
      ];

      // Create a session with context
      const params: CreateSessionParams = {
        imageId: "linux_latest",
        contextSync: persistenceData
      };

      log("Creating a session with context...");
      const createResponse = await agentBay.create(params);
      expect(createResponse.success).toBe(true);

      const session = createResponse.session;
      log(`Session created with ID: ${session.sessionId}`);

      // Create a test file in the session
      try {
        const testCmd = "echo 'test file for agentbay delete' > /home/wuying/test2/testfile2.txt";
        const cmdResult = await session.command.executeCommand(testCmd);
        log(`Created test file: ${cmdResult}`);
      } catch (error) {
        log(`Warning: Failed to create test file: ${error}`);
      }

      // Delete session with AgentBay.delete and syncContext=true
      log("Deleting session with AgentBay.delete and syncContext=true...");
      const deleteResult = await agentBay.delete(session, true);
      expect(deleteResult.success).toBe(true);
      log(`Session deleted with AgentBay.delete and syncContext=true (RequestId: ${deleteResult.requestId || "undefined"})`);

      // Verify the session was deleted
      const listResult = await agentBay.listByLabels();
      expect(listResult.success).toBe(true);
      
      // Check that our session is not in the list
      const sessions = listResult.data || [];
      for (const s of sessions) {
        expect(s.sessionId).not.toBe(session.sessionId);
      }

      // Clean up context
      try {
        const getContextResult = await agentBay.context.get(contextName);
        if (getContextResult.context) {
          const deleteContextResult = await agentBay.context.delete(getContextResult.context);
          log(`Context ${contextId} deleted (Success: ${deleteContextResult.success})`);
        }
      } catch (error) {
        log(`Warning: Failed to clean up context: ${error}`);
      }
    } catch (error) {
      fail(`Test failed with error: ${error}`);
    }
  });
}); 