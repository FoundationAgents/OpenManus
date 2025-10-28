/**
 * Basic example of using the Agent module to execute tasks.
 * This example demonstrates:
 * - Creating a session with Agent capabilities
 * - Executing a simple task using natural language
 * - Handling task results
 */

import { AgentBay } from 'wuying-agentbay-sdk';

async function main() {
  // Get API key from environment variable
  const apiKey = process.env.AGENTBAY_API_KEY;
  if (!apiKey) {
    console.log("Error: AGENTBAY_API_KEY environment variable not set");
    return;
  }

  // Initialize AgentBay client
  console.log("Initializing AgentBay client...");
  const agentBay = new AgentBay({ apiKey });

  try {
    // Create a session
    console.log("Creating a new session...");
    const sessionResult = await agentBay.create();

    if (sessionResult.success) {
      const session = sessionResult.session;
      console.log(`Session created with ID: ${session.sessionId}`);

      // Execute a task using the Agent
      const taskDescription = "Calculate the square root of 144";
      console.log(`Executing task: ${taskDescription}`);
      
      const executionResult = await session.agent.executeTask(taskDescription, 5);
      
      if (executionResult.success) {
        console.log("Task completed successfully!");
        console.log(`Task ID: ${executionResult.taskId}`);
        console.log(`Task status: ${executionResult.taskStatus}`);
      } else {
        console.log(`Task failed: ${executionResult.errorMessage}`);
        if (executionResult.taskId) {
          console.log(`Task ID: ${executionResult.taskId}`);
        }
      }

      // Clean up - delete the session
      const deleteResult = await agentBay.delete(session);
      if (deleteResult.success) {
        console.log("Session deleted successfully");
      } else {
        console.log(`Failed to delete session: ${deleteResult.errorMessage}`);
      }
    } else {
      console.log(`Failed to create session: ${sessionResult.errorMessage}`);
    }
  } catch (error) {
    console.error("Error in main function:", error);
  }
}

if (require.main === module) {
  main().catch(console.error);
}