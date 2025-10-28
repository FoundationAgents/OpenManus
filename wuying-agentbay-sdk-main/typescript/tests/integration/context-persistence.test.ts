import { AgentBay, Session, Context, newContextSync } from "../../src";
import { getTestApiKey, randomString } from "../utils/test-helpers";
import { log } from "../../src/utils/logger";

// Define Node.js process if it's not available
declare var process: {
  env: {
    [key: string]: string | undefined;
  };
};

// Helper function to check if a string contains "tool not found"
function containsToolNotFound(s: string): boolean {
  return s.toLowerCase().includes("tool not found");
}

// Helper function to check if a string contains "context not found"
function containsContextNotFoundError(s: string): boolean {
  return s.toLowerCase().includes("context not found");
}

describe("Context Persistence Integration", () => {
  let agentBay: AgentBay;
  let testContextName: string;
  let testContextId: string;
  let testContext: Context | null;
  const testFilePath = `~/test-file-${Date.now()}.txt`;
  const testFileContent = "This is a test file for context persistence";
  const testFileMode = "664"; // Read and write for owner only

  // Increase timeout for integration tests
  jest.setTimeout(120000); // 120 seconds

  beforeEach(async () => {
    const apiKey = getTestApiKey();
    agentBay = new AgentBay({ apiKey });
    testContextName = `test-context-${randomString()}`;

    // List existing contexts before creation
    try {
      const existingContextsResponse = await agentBay.context.list();
      log(
        `Found ${existingContextsResponse.contexts.length} existing contexts before creation`
      );
      log(
        `List Contexts RequestId: ${
          existingContextsResponse.requestId || "undefined"
        }`
      );
    } catch (error) {
      log(`Warning: Failed to list existing contexts: ${error}`);
      testContext = null;
    }

    // Create test context
    try {
      const createContextResponse = await agentBay.context.create(
        testContextName
      );
      if (createContextResponse.context) {
        testContext = createContextResponse.context;
        testContextId = testContext!.id;
        log(
          `Context created successfully - ID: ${testContextId}, Name: ${
            testContext!.name
          }, State: ${testContext!.state}, OSType: ${testContext!.osType}`
        );
        log(
          `Create Context RequestId: ${
            createContextResponse.requestId || "undefined"
          }`
        );
      } else {
        throw new Error("Failed to create context: context is null");
      }
    } catch (error) {
      throw new Error(`Error creating context: ${error}`);
    }
  });

  afterEach(async () => {
    if (testContext) {
      // Delete the test context
      log(`Cleaning up: Deleting test context: ${testContextName}`);
      try {
        const deleteContextResponse = await agentBay.context.delete(
          testContext
        );
        log(`Context ${testContextId} deleted successfully`);
        log(
          `Delete Context RequestId: ${
            deleteContextResponse.requestId || "undefined"
          }`
        );
      } catch (error) {
        log(`Warning: Error deleting context: ${error}`);
      }
    }
  });

  it("should persist files between sessions in the same context", async () => {
    // Add describe info
    log(
      "Test Case: Verifying file persistence between sessions in the same context"
    );
    if (!testContextId) {
      log("Skipping test as test context creation failed");
      throw new Error("Test context creation failed");
    }

    // Create first session with context sync
    let session1: Session;
    try {
      const contextSync = newContextSync(testContextId, "/home/wuying");
      
      const createSession1Response = await agentBay.create({
        imageId: "linux_latest",
        contextSync: [contextSync],
      });
      session1 = createSession1Response.session!;
      log(`First session created with ID: ${session1.sessionId}`);
      log(
        `Create Session 1 RequestId: ${
          createSession1Response.requestId || "undefined"
        }`
      );

      // Check if file exists before creating it
      const checkCmd = `ls -la ${testFilePath} 2>&1 || echo 'File does not exist'`;
      const checkResponse = await session1.command?.executeCommand(checkCmd);
      log(`Pre-check output: ${checkResponse?.output}`);
      log(
        `Check Command RequestId: ${checkResponse?.requestId || "undefined"}`
      );

      // Create test file
      const createFileCmd = `echo '${testFileContent}' > ${testFilePath}`;
      const createResponse = await session1.command?.executeCommand(
        createFileCmd
      );
      log(`File creation output: ${createResponse?.output}`);
      log(`Create File RequestId: ${createResponse?.requestId || "undefined"}`);

      // Verify the file was created
      const verifyCmd = `cat ${testFilePath}`;
      const verifyResponse = await session1.command?.executeCommand(verifyCmd);
      log(`File content: ${verifyResponse?.output}`);
      log(`Verify File RequestId: ${verifyResponse?.requestId || "undefined"}`);

      // Check file permissions
      const modeCmd = `stat -c "%a" ${testFilePath}`;
      const modeResponse = await session1.command?.executeCommand(modeCmd);
      log(`File mode: ${modeResponse?.output}`);
      log(`Mode Command RequestId: ${modeResponse?.requestId || "undefined"}`);

      // Also check file attributes
      const lsCmd = `ls -la ${testFilePath}`;
      const lsResponse = await session1.command?.executeCommand(lsCmd);
      if (lsResponse?.output) {
        log(`File attributes: ${lsResponse.output}`);
        log(`ls Command RequestId: ${lsResponse.requestId || "undefined"}`);
      }

      if (
        !verifyResponse?.output ||
        !verifyResponse.output.includes(testFileContent)
      ) {
        throw new Error(
          `File content verification failed. Expected to contain '${testFileContent}', got: '${verifyResponse?.output}'`
        );
      }

      // Release the first session
      const deleteSession1Response = await session1.delete();
      log(
        `Delete Session 1 RequestId: ${
          deleteSession1Response.requestId || "undefined"
        }`
      );
    } catch (error) {
      if (session1!) {
        const deleteSession1Response = await session1.delete();
        log(
          `Delete Session 1 (Error) RequestId: ${
            deleteSession1Response.requestId || "undefined"
          }`
        );
      }
      throw error;
    }

    // Wait for 30 seconds to ensure the session is fully released and persisted
    log("Waiting for 30 seconds before creating the second session...");
    await new Promise((resolve) => setTimeout(resolve, 30000));

    // List active sessions before creating second session
    try {
      const activeSessions = agentBay.list();
      log(
        `Found ${activeSessions.length} active sessions before second session creation`
      );
    } catch (error) {
      log(`Warning: Failed to list active sessions: ${error}`);
    }

    // Create second session with the same context
    let session2: Session;
    try {
      const contextSync = newContextSync(testContextId, "/home/wuying");
      
      const createSession2Response = await agentBay.create({
        imageId: "linux_latest",
        contextSync: [contextSync],
      });
      if (!createSession2Response.session) {
        throw new Error("Failed to create second session: session is null");
      }
      session2 = createSession2Response.session;
      log(`Second session created with ID: ${session2.sessionId}`);
      log(
        `Create Session 2 RequestId: ${
          createSession2Response.requestId || "undefined"
        }`
      );

      // Verify the file still exists
      const verifyCmd = `cat ${testFilePath}`;
      const verifyResponse = await session2.command?.executeCommand(verifyCmd);
      log(
        `Verify File (Session 2) RequestId: ${
          verifyResponse?.requestId || "undefined"
        }`
      );

      if (
        !verifyResponse?.output ||
        !verifyResponse.output.includes(testFileContent)
      ) {
        throw new Error(
          `File persistence test failed. Expected file to exist with content '${testFileContent}', got: '${verifyResponse?.output}'`
        );
      }

      log(`File persistence verified: file exists in the second session`);
    } finally {
      if (session2!) {
        const deleteSession2Response = await session2.delete();
        log(
          `Delete Session 2 RequestId: ${
            deleteSession2Response.requestId || "undefined"
          }`
        );
      }
    }
  });

  it("should isolate files between different contexts", async () => {
    // Add describe info
    log("Test Case: Verifying file isolation between different contexts");
    if (!testContextId) {
      throw new Error("Test context creation failed");
    }

    // Create a second test context
    const secondContextName = `test-context-2-${Date.now()}`;
    let secondContext: Context;
    try {
      const createSecondContextResponse = await agentBay.context.create(
        secondContextName
      );
      secondContext = createSecondContextResponse.context!;
      log(
        `Second context created - ID: ${secondContext.id}, Name: ${secondContext.name}, State: ${secondContext.state}, OSType: ${secondContext.osType}`
      );
      log(
        `Create Second Context RequestId: ${
          createSecondContextResponse.requestId || "undefined"
        }`
      );

      // Create first session with context sync
      let session1: Session;
      try {
        const contextSync = newContextSync(testContextId, "/home/wuying");
        
        const createSession1Response = await agentBay.create({
          imageId: "linux_latest",
          contextSync: [contextSync],
        });
        session1 = createSession1Response.session!;
        log(`First session created with ID: ${session1.sessionId}`);
        log(
          `Create Session 1 RequestId: ${
            createSession1Response.requestId || "undefined"
          }`
        );

        // Create test file
        const createFileCmd = `echo '${testFileContent}' > ${testFilePath}`;
        const createResponse = await session1.command?.executeCommand(
          createFileCmd
        );
        log(`File creation output: ${createResponse?.output}`);
        log(
          `Create File RequestId: ${createResponse?.requestId || "undefined"}`
        );

        // Verify the file was created
        const verifyCmd = `cat ${testFilePath}`;
        const verifyResponse = await session1.command?.executeCommand(
          verifyCmd
        );
        log(`File content: ${verifyResponse?.output}`);
        log(
          `Verify File RequestId: ${verifyResponse?.requestId || "undefined"}`
        );

        if (
          !verifyResponse?.output ||
          !verifyResponse.output.includes(testFileContent)
        ) {
          throw new Error(
            `File content verification failed. Expected to contain '${testFileContent}', got: '${verifyResponse?.output}'`
          );
        }
      } finally {
        if (session1!) {
          const deleteSession1Response = await session1.delete();
          log(
            `Delete Session 1 RequestId: ${
              deleteSession1Response.requestId || "undefined"
            }`
          );
        }
      }

      // Create third session with the second context
      let session3: Session;
      try {
        const contextSync = newContextSync(secondContext.id, "/home/wuying");
        
        const createSession3Response = await agentBay.create({
          imageId: "linux_latest",
          contextSync: [contextSync],
        });
        session3 = createSession3Response.session!;
        log(`Third session created with ID: ${session3.sessionId}`);
        log(
          `Create Session 3 RequestId: ${
            createSession3Response.requestId || "undefined"
          }`
        );

        // Try to read the file
        const verifyCmd = `cat ${testFilePath}`;
        const checkCmd = `ls -la ${testFilePath} 2>&1 || echo 'File does not exist'`;

        // First check with ls command
        const checkResponse = await session3.command?.executeCommand(checkCmd);
        log(`ls command output in third session: ${checkResponse?.output}`);
        log(
          `Check Command (Session 3) RequestId: ${
            checkResponse?.requestId || "undefined"
          }`
        );

        // Then try to read the file content
        const verifyResponse = await session3.command?.executeCommand(
          verifyCmd
        );
        log(
          `Verify Command (Session 3) RequestId: ${
            verifyResponse?.requestId || "undefined"
          }`
        );

        if (
          verifyResponse?.output &&
          verifyResponse.output.includes(testFileContent)
        ) {
          throw new Error(
            `File isolation test failed. File unexpectedly exists in the third session with content: '${verifyResponse.output}'`
          );
        } else {
          log(
            `File isolation verified: file does not exist in the third session`
          );
        }
      } finally {
        if (session3!) {
          const deleteSession3Response = await session3.delete();
          log(
            `Delete Session 3 RequestId: ${
              deleteSession3Response.requestId || "undefined"
            }`
          );
        }
      }
    } finally {
      // Delete the second context if it was created
      if (secondContext!) {
        try {
          const deleteSecondContextResponse = await agentBay.context.delete(
            secondContext
          );
          log(`Second context ${secondContext.id} deleted successfully`);
          log(
            `Delete Second Context RequestId: ${
              deleteSecondContextResponse.requestId || "undefined"
            }`
          );
        } catch (error) {
          log(`Warning: Error deleting second context: ${error}`);
        }
      }
    }
  });
});
