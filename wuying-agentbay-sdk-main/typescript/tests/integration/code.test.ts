import { AgentBay, Session } from "../../src";
import { getTestApiKey } from "../utils/test-helpers";
import { log, logError } from "../../src/utils/logger";

describe("Code Integration Test", () => {
  describe("runCode", () => {
    let agentBay: AgentBay;
    let session: Session;

    beforeEach(async () => {
      const apiKey = getTestApiKey();
      agentBay = new AgentBay({ apiKey });

      log("Creating a new session for code testing...");
      
      // Create session with code_latest image for code execution tests
      const createResponse = await agentBay.create({ imageId: "code_latest" });
      session = createResponse.session!;
      log(`Session created with ID: ${session.sessionId}`);
    });

    afterEach(async () => {
      if (session) {
        log(`Cleaning up session: ${session.sessionId}`);
        try {
          await session.delete();
        } catch (error) {
          logError("Failed to delete session:", error);
        }
      }
    });

    test("should execute Python code successfully", async () => {
      if (!session || !session.code) {
        log("Note: Code interface is nil, skipping code test");
        return;
      }

      const pythonCode = `
print("Hello, world!")
x = 1 + 1
print(x)
`;

      log("Executing Python code...");

      const runCodeResponse = await session.code.runCode(pythonCode, "python");

      log(`Python code execution output:`, runCodeResponse.result);
      log(`Run Code RequestId: ${runCodeResponse.requestId || "undefined"}`);

      expect(runCodeResponse.success).toBe(true);
      expect(runCodeResponse.requestId).toBeDefined();
      expect(typeof runCodeResponse.requestId).toBe("string");

      expect(runCodeResponse.result).toBeDefined();
      expect(runCodeResponse.result.includes("Hello, world!")).toBe(true);
      expect(runCodeResponse.result.includes("2")).toBe(true);
    }, 60000);

    test("should execute JavaScript code successfully", async () => {
      if (!session || !session.code) {
        log("Note: Code interface is nil, skipping code test");
        return;
      }

      const jsCode = `
console.log("Hello, world!");
const x = 1 + 1;
console.log(x);
`;

      log("Executing JavaScript code...");

      const runCodeResponse = await session.code.runCode(jsCode, "javascript");

      log(`JavaScript code execution output:`, runCodeResponse.result);
      log(`Run Code RequestId: ${runCodeResponse.requestId || "undefined"}`);

      expect(runCodeResponse.success).toBe(true);
      expect(runCodeResponse.requestId).toBeDefined();
      expect(typeof runCodeResponse.requestId).toBe("string");

      expect(runCodeResponse.result).toBeDefined();
      expect(runCodeResponse.result.includes("Hello, world!")).toBe(true);
      expect(runCodeResponse.result.includes("2")).toBe(true);
    }, 60000);

    test("should handle unsupported language", async () => {
      if (!session || !session.code) {
        log("Note: Code interface is nil, skipping code test");
        return;
      }

      log("Testing with unsupported language...");

      const response = await session.code.runCode('print("test")', "ruby");

      expect(response.success).toBe(false);
      expect(response.errorMessage).toBeDefined();
      expect(response.errorMessage).toContain("Unsupported language");
    }, 30000);
  });
}); 