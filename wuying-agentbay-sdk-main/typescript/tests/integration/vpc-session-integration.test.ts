import { AgentBay, Session } from "../../src";
import { getTestApiKey } from "../utils/test-helpers";
import { log } from "../../src/utils/logger";

/**
 * VPC Session Integration Tests
 * 
 * Tests the creation of VPC-based sessions and various functionality:
 * 1. Create sessions with isVpc=true  
 * 2. Test FileSystem writeFile/readFile functionality
 * 3. Test Command executeCommand functionality
 * 4. Clean up sessions
 * 
 * Note: This test is designed to verify that VPC sessions can be created 
 * and core operations work correctly.
 */

describe("VPC Session Integration", () => {
  let agentBay: AgentBay;

  beforeEach(() => {
    const apiKey = getTestApiKey();
    log(`Using API key: ${apiKey}`);

    agentBay = new AgentBay({ apiKey });
    log(`AgentBay client initialized successfully`);
  });

  describe("VPC Session Basic Tools", () => {
    it("should create VPC session and test filesystem write/read functionality", async () => {
      try {
        log("=".repeat(80));
        log("TEST: VPC Session Basic Tools");
        log("=".repeat(80));

        // Step 1: Create a VPC-based session
        log("Step 1: Creating VPC-based session...");
        const params = {
          imageId: "imgc-07eksy57nw6r759fb",
          isVpc: true,
          labels: {
            "test-type": "vpc-integration",
            "purpose": "vpc-session-testing"
          }
        };

        log(`Session params: ImageId=${params.imageId}, IsVpc=${params.isVpc}, Labels=${JSON.stringify(params.labels)}`);

        const sessionResult = await agentBay.create(params);
        expect(sessionResult.success).toBe(true);
        expect(sessionResult.session).toBeDefined();
        
        const session = sessionResult.session!;
        log(`VPC session created successfully with ID: ${session.sessionId} (RequestID: ${sessionResult.requestId})`);

        try {
        // Verify session properties
        expect(session.sessionId).toBeDefined();
        expect(session.sessionId.length).toBeGreaterThan(0);
        log(`Session properties verified: ID=${session.sessionId}`);

        // Step 2: Test Command functionality to create a file
        log("Step 2: Testing Command functionality to create a file...");
        if (session.command) {
          log("✓ Command tool is available in VPC session");

          // Test file path and content
          const testFilePath = "/tmp/vpc_test_file.txt";
          const testContent = `Hello from VPC session!\\nThis is a test file written by the VPC integration test.\\nTimestamp: ${new Date().toISOString()}`;

          log(`Testing executeCommand to create file: ${testFilePath}`);
          log(`Test content length: ${testContent.length} characters`);

          // Use echo command to write content to file
          const writeCommand = `echo '${testContent}' > ${testFilePath}`;
          log(`Execute command: ${writeCommand}`);

          const cmdResult = await session.command.executeCommand(writeCommand);
          if (cmdResult.success) {
            log(`✓ executeCommand successful - Output: ${cmdResult.output}, RequestID: ${cmdResult.requestId}`);
            log("✓ File creation command executed successfully");

            // Verify RequestID is present
            if (cmdResult.requestId) {
              log("✓ executeCommand returned RequestID");
            } else {
              log("⚠ executeCommand did not return RequestID");
            }
          } else {
            log(`⚠ executeCommand failed: ${cmdResult.errorMessage}`);
          }
        } else {
          log("⚠ Command tool is not available in VPC session");
        }

        // Step 3: Test FileSystem readFile functionality to verify written content
        log("Step 3: Testing FileSystem readFile functionality to verify written content...");
        if (session.fileSystem) {
          // Test reading the file we just wrote
          const testFilePath = "/tmp/vpc_test_file.txt";
          log(`Testing readFile with path: ${testFilePath}`);

          const readResult = await session.fileSystem.readFile(testFilePath);
          if (readResult.success) {
            log(`✓ readFile successful - Content length: ${readResult.content.length} bytes, RequestID: ${readResult.requestId}`);

            // Log first 200 characters of content for verification
            let contentPreview = readResult.content;
            if (contentPreview.length > 200) {
              contentPreview = contentPreview.substring(0, 200) + "...";
            }
            log(`Content preview: ${contentPreview}`);

            // Verify that content is not empty
            expect(readResult.content.length).toBeGreaterThan(0);
            log("✓ readFile returned non-empty content");

            // Verify that content contains expected test content
            if (readResult.content.includes("Hello from VPC session!")) {
              log("✓ readFile content contains expected test message");
            } else {
              log("⚠ readFile content does not contain expected test message");
            }

            if (readResult.content.includes("This is a test file written by the VPC integration test")) {
              log("✓ readFile content contains expected test description");
            } else {
              log("⚠ readFile content does not contain expected test description");
            }

            // Verify RequestID is present
            if (readResult.requestId) {
              log("✓ readFile returned RequestID");
            } else {
              log("⚠ readFile did not return RequestID");
            }
          } else {
            log(`⚠ readFile failed: ${readResult.errorMessage}`);
          }
        } else {
          log("⚠ FileSystem tool is not available in VPC session");
        }

      } finally {
        // Ensure cleanup of the session at the end of the test
        log("Cleaning up: Deleting the VPC session...");
        const deleteResult = await agentBay.delete(session);
        if (deleteResult.success) {
          log(`VPC session successfully deleted (RequestID: ${deleteResult.requestId})`);
        } else {
          log(`Warning: Error deleting VPC session: ${deleteResult.errorMessage}`);
        }
      }

      log("VPC session filesystem write/read test completed successfully");
      } catch (error) {
        log(`Error in VPC Session Basic Tools test: ${error}`);
        throw error;
      }
    });
  });
});

