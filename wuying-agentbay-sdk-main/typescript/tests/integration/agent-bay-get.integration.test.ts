import { AgentBay } from "../../src/agent-bay";
import { Session } from "../../src/session";

describe("AgentBay.get integration tests", () => {
  let agentBay: AgentBay;
  let sessionId: string | undefined;
  let sessionCreated: boolean = false;

  beforeAll(async () => {
    const apiKey = process.env.AGENTBAY_API_KEY;
    if (!apiKey) {
      throw new Error("AGENTBAY_API_KEY environment variable is not set");
    }
    agentBay = new AgentBay({ apiKey });

    console.log("Creating a new session for Get API testing...");

    try {
      // Create session
      const createResult = await agentBay.create();
      if (createResult.success && createResult.session) {
        sessionId = createResult.session.sessionId;
        sessionCreated = true;
        console.log(`Session created with ID: ${sessionId}`);
      } else {
        console.log("Session creation failed, some tests will be skipped");
      }
    } catch (error) {
      console.log(`Session creation error: ${error}, some tests will be skipped`);
    }
  }, 60000); // 60 second timeout for session creation

  test("should retrieve session using Get API", async () => {
    if (!sessionCreated || !sessionId) {
      console.log("Skipping test: session was not created");
      return;
    }

    console.log("Testing Get API...");
    const result = await agentBay.get(sessionId);

    expect(result).toBeDefined();
    expect(result.success).toBe(true);
    expect(result.requestId).toBeDefined();
    expect(result.session).toBeDefined();
    expect(result.session).toBeInstanceOf(Session);
    expect(result.session!.sessionId).toBe(sessionId);

    console.log(`Successfully retrieved session with ID: ${result.session!.sessionId}`);
    console.log(`Request ID: ${result.requestId}`);
    console.log("Get API test passed successfully");
  }, 30000); // 30 second timeout

  test("should return error for non-existent session", async () => {
    console.log("Testing Get API with non-existent session ID...");
    const nonExistentSessionId = "session-nonexistent-12345";

    const result = await agentBay.get(nonExistentSessionId);
    
    expect(result).toBeDefined();
    expect(result.success).toBe(false);
    expect(result.errorMessage).toContain("Failed to get session");

    console.log("Correctly received error for non-existent session");
    console.log("Get API non-existent session test passed successfully");
  }, 30000); // 30 second timeout

  test("should return error for empty session ID", async () => {
    console.log("Testing Get API with empty session ID...");

    const result = await agentBay.get("");
    
    expect(result).toBeDefined();
    expect(result.success).toBe(false);
    expect(result.errorMessage).toContain("session_id is required");

    console.log("Correctly received error for empty session ID");
    console.log("Get API empty session ID test passed successfully");
  });

  test("should return error for whitespace session ID", async () => {
    console.log("Testing Get API with whitespace session ID...");

    const result = await agentBay.get("   ");
    
    expect(result).toBeDefined();
    expect(result.success).toBe(false);
    expect(result.errorMessage).toContain("session_id is required");

    console.log("Correctly received error for whitespace session ID");
    console.log("Get API whitespace session ID test passed successfully");
  });

  afterAll(async () => {
    if (!sessionCreated || !sessionId) {
      console.log("No session to clean up");
      return;
    }

    console.log("Cleaning up: Deleting the session...");
    try {
      const result = await agentBay.get(sessionId); // Retrieve session object
      if (result.success && result.session) {
        const deleteResult = await result.session.delete();
        if (deleteResult.success) {
          console.log(`Session ${sessionId} deleted successfully`);
        } else {
          console.warn(
            `Warning: Failed to delete session: ${deleteResult.errorMessage}`
          );
        }
      }
    } catch (error) {
      console.warn(`Warning: Failed to clean up session: ${error}`);
    }
  }, 30000); // 30 second timeout
});

