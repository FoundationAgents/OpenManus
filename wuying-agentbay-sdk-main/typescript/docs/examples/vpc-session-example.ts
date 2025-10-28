/**
 * Basic example of creating and using a VPC session.
 * This example demonstrates:
 * - Creating a VPC session with specific parameters
 * - Using FileSystem operations in a VPC session
 * - Using Command execution in a VPC session
 * - Proper session cleanup
 */

import { AgentBay, newCreateSessionParams } from 'wuying-agentbay-sdk';

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
    // Create a VPC session
    console.log("Creating a VPC session...");
    const params = newCreateSessionParams()
      .withImageId("linux_latest")
      .withIsVpc(true)
      .withLabels({
        "test-type": "vpc-basic-example",
        "purpose": "demonstration",
        "timestamp": Math.floor(Date.now() / 1000).toString()
      });

    const sessionResult = await agentBay.create(params);

    if (!sessionResult.success) {
      console.log(`Failed to create VPC session: ${sessionResult.errorMessage}`);
      return;
    }

    const session = sessionResult.session;
    console.log(`VPC session created successfully with ID: ${session.sessionId}`);

    try {
      // Test FileSystem operations
      console.log("\n--- Testing FileSystem operations ---");
      const testFilePath = "/tmp/vpc_example_test.txt";
      const testContent = `Hello from VPC session! Created at ${new Date().toISOString()}`;

      // Write file
      const writeResult = await session.fileSystem.writeFile(testFilePath, testContent);
      if (writeResult.success) {
        console.log("✓ File written successfully");
      } else {
        console.log(`⚠ File write failed: ${writeResult.errorMessage}`);
      }

      // Read file
      const readResult = await session.fileSystem.readFile(testFilePath);
      if (readResult.success) {
        console.log(`✓ File read successfully. Content: ${readResult.content}`);
      } else {
        console.log(`⚠ File read failed: ${readResult.errorMessage}`);
      }

      // Test Command operations
      console.log("\n--- Testing Command operations ---");

      // Get current user
      const cmdResult = await session.command.executeCommand("whoami");
      if (cmdResult.success) {
        console.log(`✓ Current user: ${cmdResult.output.trim()}`);
      } else {
        console.log(`⚠ Command execution failed: ${cmdResult.errorMessage}`);
      }

      // List directory contents
      const lsResult = await session.command.executeCommand("ls -la /tmp");
      if (lsResult.success) {
        console.log("✓ Directory listing successful");
        console.log(`  Output:\n${lsResult.output}`);
      } else {
        console.log(`⚠ Directory listing failed: ${lsResult.errorMessage}`);
      }

    } finally {
      // Clean up - delete the session
      console.log("\n--- Cleaning up ---");
      const deleteResult = await agentBay.delete(session);
      if (deleteResult.success) {
        console.log("✓ VPC session deleted successfully");
      } else {
        console.log(`⚠ Failed to delete VPC session: ${deleteResult.errorMessage}`);
      }
    }

  } catch (error) {
    console.error("Error in main function:", error);
  }
}

if (require.main === module) {
  main().catch(console.error);
}
