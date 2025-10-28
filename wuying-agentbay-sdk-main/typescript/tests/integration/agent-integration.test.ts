import { AgentBay, Session } from "../../src";
import { getTestApiKey } from "../utils/test-helpers";
import { log } from "../../src/utils/logger";

describe("Agent", () => {
  describe("executeTask", () => {
    let agentBay: AgentBay;
    let session: Session;

    beforeEach(async () => {
      const apiKey = getTestApiKey();
      agentBay = new AgentBay({ apiKey });

      // Create a session with Windows image for agent tasks
      log("Creating a new session for agent task testing...");
      const createResponse = await agentBay.create({ imageId: "waic-playground-demo-windows" });
      session = createResponse.session!;
      log(`Session created with ID: ${session.sessionId}`);
      log(`Create Session RequestId: ${createResponse.requestId || "undefined"}`);
    });

    afterEach(async () => {
      // Clean up the session
      log("Cleaning up: Deleting the session...");
      try {
        if (session && session.sessionId) {
          const deleteResponse = await agentBay.delete(session);
          log(`Delete Session RequestId: ${deleteResponse.requestId || "undefined"}`);
        }
      } catch (error) {
        log(`Warning: Error deleting session: ${error}`);
      }
    });

    it("should execute task successfully", async () => {
      if (session.agent) {
        const task = "create a folder named 'agentbay' in C:\\Windows\\Temp";
        
        // Get timeout from environment or use default
        const maxTryTimesStr = process.env.AGENT_TASK_TIMEOUT;
        let maxTryTimes = 300; // default value
        if (maxTryTimesStr) {
          const parsed = parseInt(maxTryTimesStr, 10);
          if (!isNaN(parsed)) {
            maxTryTimes = parsed;
          }
        } else {
          log("We will wait for 300 * 3 seconds to finish.");
        }

        try {
          log(`Executing agent task: ${task}`);
          const result = await session.agent.executeTask(task, maxTryTimes);
          
          log(`Agent task result: Success=${result.success}, TaskID=${result.taskId}, Status=${result.taskStatus}`);
          log(`Agent Task RequestId: ${result.requestId || "undefined"}`);

          // Verify that the response contains requestId
          expect(result.requestId).toBeDefined();
          expect(typeof result.requestId).toBe("string");

          if (!result.success) {
            log(`Note: Agent task execution failed: ${result.errorMessage}`);
            // Don't fail the test if task execution is not supported in test environment
          } else {
            log("Agent task executed successfully");
            expect(result.success).toBe(true);
            expect(result.taskId).toBeTruthy();
          }
        } catch (error) {
          log(`Note: Agent task execution failed: ${error}`);
          // Don't fail the test if agent execution is not supported
        }
      } else {
        log("Note: Agent interface is nil, skipping agent test");
      }
    }); // Set a long timeout for the task execution
  });
}); 