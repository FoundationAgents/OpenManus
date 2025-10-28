/**
 * Example demonstrating how to use the Get API to retrieve a session by its ID.
 *
 * This example shows:
 * 1. Creating a session
 * 2. Retrieving the session using the Get API
 * 3. Using the session for operations
 * 4. Cleaning up resources
 */

import { AgentBay } from "../../../src/agent-bay";

async function main() {
  // Get API key from environment variable
  const apiKey = process.env.AGENTBAY_API_KEY;
  if (!apiKey) {
    throw new Error("AGENTBAY_API_KEY environment variable is not set");
  }

  // Initialize AgentBay client
  const agentBay = new AgentBay({ apiKey });

  // For demonstration, first create a session
  console.log("Creating a session...");
  const createResult = await agentBay.create();
  if (!createResult.success || !createResult.session) {
    throw new Error(`Failed to create session: ${createResult.errorMessage}`);
  }

  const sessionId = createResult.session.sessionId;
  console.log(`Created session with ID: ${sessionId}`);

  // Retrieve the session by ID using Get API
  console.log("\nRetrieving session using Get API...");
  const getResult = await agentBay.get(sessionId);
  
  if (!getResult.success || !getResult.session) {
    throw new Error(`Failed to get session: ${getResult.errorMessage}`);
  }
  
  const session = getResult.session;

  // Display session information
  console.log("Successfully retrieved session:");
  console.log(`  Session ID: ${session.sessionId}`);
  console.log(`  Request ID: ${getResult.requestId}`);

  // The session object can be used for further operations
  // For example, you can execute commands, work with files, etc.
  console.log("\nSession is ready for use");

  // Clean up: Delete the session when done
  console.log("\nCleaning up...");
  const deleteResult = await session.delete();

  if (deleteResult.success) {
    console.log(`Session ${sessionId} deleted successfully`);
  } else {
    console.log(`Failed to delete session ${sessionId}`);
  }
}

main().catch((error) => {
  console.error("Error:", error);
  process.exit(1);
});

