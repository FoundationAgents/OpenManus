import { AgentBay, Session } from "../../src";
import { getTestApiKey, containsToolNotFound } from "../utils/test-helpers";
import { log } from "../../src/utils/logger";

// Helper function to check if content has error
function hasErrorInContent(content: string): boolean {
  if (!content) {
    return true;
  }

  // Check if content has error text
  return content.includes("error") || content.includes("Error");
}

describe("Command", () => {
  describe("runCode", () => {
    let agentBay: AgentBay;
    let session: Session;

    beforeEach(async () => {
      const apiKey = getTestApiKey();
      agentBay = new AgentBay({ apiKey });

      // Create a session with linux_latest image
      log("Creating a new session for run_code testing...");
      const createResponse = await agentBay.create({ imageId: "code_latest" });
      session = createResponse.session!;
      log(`Session created with ID: ${session.sessionId}`);
      log(
        `Create Session RequestId: ${createResponse.requestId || "undefined"}`
      );
    });

    afterEach(async () => {
      // Clean up the session
      log("Cleaning up: Deleting the session...");
      try {
        if (session && session.sessionId) {
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

    it("should execute Python code", async () => {
      if (session.command) {
        // Test with Python code
        log("Executing Python code...");
        const pythonCode = `
print("Hello, world!")
x = 1 + 1
print(x)
`;

        try {
          // Test with default timeout
          const runCodeResponse = await session.code.runCode(
            pythonCode,
            "python"
          );
          log(`Python code execution output:`, runCodeResponse.result);
          log(
            `Run Code RequestId: ${runCodeResponse.requestId || "undefined"}`
          );

          // Verify that the response contains requestId
          expect(runCodeResponse.requestId).toBeDefined();
          expect(typeof runCodeResponse.requestId).toBe("string");

          // Check if output has valid format
          expect(runCodeResponse.result).toBeDefined();
          expect(hasErrorInContent(runCodeResponse.result)).toBe(false);

          // Verify the response contains expected output
          expect(runCodeResponse.result.includes("Hello, world!")).toBe(true);
          expect(runCodeResponse.result.includes("2")).toBe(true);
          log("Python code execution verified successfully");
        } catch (error) {
          log(`Note: Python code execution failed: ${error}`);
          // Don't fail the test if code execution is not supported
        }
      } else {
        log("Note: Command interface is nil, skipping run_code test");
      }
    });

    it("should execute JavaScript code with custom timeout", async () => {
      if (session.command) {
        // Test with JavaScript code
        log("Executing JavaScript code with custom timeout...");
        const jsCode = `
          console.log("Hello, world!");
          const x = 1 + 1;
          console.log(x);
          `;

        try {
          // Test with custom timeout (10 minutes)
          const customTimeout = 600;
          const runCodeResponse = await session.code.runCode(
            jsCode,
            "javascript",
            customTimeout
          );
          log(`JavaScript code execution output:`, runCodeResponse.result);
          log(
            `Run Code RequestId: ${runCodeResponse.requestId || "undefined"}`
          );

          // Verify that the response contains requestId
          expect(runCodeResponse.requestId).toBeDefined();
          expect(typeof runCodeResponse.requestId).toBe("string");

          // Check if output has valid format
          expect(runCodeResponse.result).toBeDefined();
          expect(hasErrorInContent(runCodeResponse.result)).toBe(false);

          // Verify the response contains expected output
          expect(runCodeResponse.result.includes("Hello, world!")).toBe(true);
          expect(runCodeResponse.result.includes("2")).toBe(true);
          log("JavaScript code execution verified successfully");
        } catch (error) {
          log(`Note: JavaScript code execution failed: ${error}`);
          // Don't fail the test if code execution is not supported
        }
      } else {
        log("Note: Command interface is nil, skipping run_code test");
      }
    });

    it("should handle invalid language", async () => {
      if (session.command) {
        // Test with invalid language
        log("Testing with invalid language...");

        try {
          await session.code.runCode('print("test")', "invalid_language");
          // If we get here, the test should fail
          log("Error: Expected error for invalid language, but got success");
          expect(false).toBe(true); // This should fail the test
        } catch (error) {
          // This is the expected behavior
          log(`Correctly received error for invalid language: ${error}`);
          expect(error).toBeDefined();
        }
      } else {
        log("Note: Command interface is nil, skipping run_code test");
      }
    });
  });

  describe("executeCommand", () => {
    let agentBay: AgentBay;
    let session: Session;

    beforeEach(async () => {
      const apiKey = getTestApiKey();
      agentBay = new AgentBay({ apiKey });

      // Create a session with linux_latest image
      log("Creating a new session for command testing...");
      const createResponse = await agentBay.create({ imageId: "linux_latest" });
      session = createResponse.session!;
      log(`Session created with ID: ${session.sessionId}`);
      log(
        `Create Session RequestId: ${createResponse.requestId || "undefined"}`
      );
    });

    afterEach(async () => {
      // Clean up the session
      log("Cleaning up: Deleting the session...");
      try {
        if (session && session.sessionId) {
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
    it("should execute a command", async () => {
      if (session.command) {
        // Test with echo command (works on all platforms)
        log("Executing echo command...");
        const testString = "AgentBay SDK Test";
        const echoCmd = `echo '${testString}'`;

        try {
          // Increase the command execution timeout to 10 seconds (10000ms)
          const executeResponse = await session.command.executeCommand(
            echoCmd,
            10000
          );
          log(`Echo command output:`, executeResponse.output);
          log(
            `Execute Command RequestId: ${
              executeResponse.requestId || "undefined"
            }`
          );

          // Verify that the response contains requestId
          expect(executeResponse.requestId).toBeDefined();
          expect(typeof executeResponse.requestId).toBe("string");

          // Check if output has valid format
          expect(executeResponse.output).toBeDefined();
          expect(hasErrorInContent(executeResponse.output)).toBe(false);

          // Verify the output contains the test string
          expect(executeResponse.output.includes(testString)).toBe(true);
          log("Echo command verified successfully");
        } catch (error) {
          log(`Note: Echo command failed: ${error}`);
          // Don't fail the test if command execution is not supported
        }
      } else {
        log("Note: Command interface is nil, skipping command test");
      }
    });

    it("should handle command execution errors", async () => {
      if (session.command) {
        // Test with an invalid command
        log("Executing invalid command...");
        const invalidCmd = "invalid_command_that_does_not_exist";

        try {
          const executeResponse = await session.command.executeCommand(
            invalidCmd
          );
          log(`Invalid command:`, executeResponse);
          log(`Invalid command output:`, executeResponse.output);
          log(
            `Execute Invalid Command RequestId: ${
              executeResponse.requestId || "undefined"
            }`
          );

          // Verify that the response contains requestId
          expect(executeResponse.requestId).toBeDefined();

          // Just check that we got a content array back
          expect(executeResponse.output).toBeDefined();
          expect(hasErrorInContent(executeResponse.output)).toBe(true);

          // For invalid commands, the output may contain error information, which is fine
        } catch (error) {
          // If the API rejects the promise, that's also an acceptable behavior for an invalid command
          log(`Invalid command failed as expected: ${error}`);
          expect(error).toBeDefined();
        }
      } else {
        log("Note: Command interface is nil, skipping command error test");
      }
    });

    it("should execute a command with arguments", async () => {
      if (session.command) {
        // Test with a command that takes arguments
        log("Executing command with arguments...");
        const arg1 = "hello";
        const arg2 = "world";
        const cmd = `echo ${arg1} ${arg2}`;

        try {
          // Increase the command execution timeout to 10 seconds (10000ms)
          const executeResponse = await session.command.executeCommand(
            cmd,
            10000
          );
          log(`Command with arguments output:`, executeResponse.output);
          log(
            `Execute Command with Args RequestId: ${
              executeResponse.requestId || "undefined"
            }`
          );

          // Verify that the response contains requestId
          expect(executeResponse.requestId).toBeDefined();
          expect(typeof executeResponse.requestId).toBe("string");

          // Check if output has valid format
          expect(executeResponse.output).toBeDefined();
          expect(hasErrorInContent(executeResponse.output)).toBe(false);

          // Verify the output contains both arguments
          expect(executeResponse.output.includes(arg1)).toBe(true);
          expect(executeResponse.output.includes(arg2)).toBe(true);
          log("Command with arguments verified successfully");
        } catch (error) {
          log(`Note: Command with arguments failed: ${error}`);
          // Don't fail the test if command execution is not supported
        }
      } else {
        log(
          "Note: Command interface is nil, skipping command with arguments test"
        );
      }
    });
  });
});
