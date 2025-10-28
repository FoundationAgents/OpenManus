/**
 * AgentBay List Sessions Example
 *
 * This example demonstrates how to use the list() API to query sessions with filtering and pagination.
 *
 * Features demonstrated:
 * 1. List all sessions
 * 2. List sessions with label filtering
 * 3. List sessions with pagination
 * 4. Handle pagination to retrieve all results
 *
 * Usage:
 *     npx ts-node main.ts
 */

import { AgentBay, CreateSessionParams, Session } from "../../../src";

async function main() {
  // Get API key from environment variable
  const apiKey = process.env.AGENTBAY_API_KEY;
  if (!apiKey) {
    console.error("Error: AGENTBAY_API_KEY environment variable not set");
    console.error(
      "Please set your API key: export AGENTBAY_API_KEY='your-api-key'"
    );
    process.exit(1);
  }

  // Initialize AgentBay client
  const agentBay = new AgentBay({ apiKey });
  console.log("✅ AgentBay client initialized");

  // Create some test sessions with labels for demonstration
  console.log("\n📝 Creating test sessions...");
  const testSessions: Session[] = [];

  try {
    // Create session 1 with labels
    const params1: CreateSessionParams = {
      labels: {
        project: "list-demo",
        environment: "dev",
        owner: "demo-user",
      },
    };
    const result1 = await agentBay.create(params1);
    if (result1.success && result1.session) {
      testSessions.push(result1.session);
      console.log(`✅ Created session 1: ${result1.session.sessionId}`);
      console.log(`   Request ID: ${result1.requestId}`);
    }

    // Create session 2 with labels
    const params2: CreateSessionParams = {
      labels: {
        project: "list-demo",
        environment: "staging",
        owner: "demo-user",
      },
    };
    const result2 = await agentBay.create(params2);
    if (result2.success && result2.session) {
      testSessions.push(result2.session);
      console.log(`✅ Created session 2: ${result2.session.sessionId}`);
      console.log(`   Request ID: ${result2.requestId}`);
    }

    // Create session 3 with labels
    const params3: CreateSessionParams = {
      labels: {
        project: "list-demo",
        environment: "prod",
        owner: "demo-user",
      },
    };
    const result3 = await agentBay.create(params3);
    if (result3.success && result3.session) {
      testSessions.push(result3.session);
      console.log(`✅ Created session 3: ${result3.session.sessionId}`);
      console.log(`   Request ID: ${result3.requestId}`);
    }
  } catch (error) {
    console.error(`❌ Error creating test sessions: ${error}`);
    process.exit(1);
  }

  try {
    // Example 1: List all sessions (no filter)
    console.log("\n" + "=".repeat(60));
    console.log("Example 1: List all sessions (no filter)");
    console.log("=".repeat(60));

    const result = await agentBay.list();
    if (result.success) {
      console.log(`✅ Found ${result.totalCount} total sessions`);
      console.log(`📄 Showing ${result.sessionIds.length} session IDs on this page`);
      console.log(`🔑 Request ID: ${result.requestId}`);
      console.log(`📊 Max results per page: ${result.maxResults}`);

      // Display first few sessions
      for (let i = 0; i < Math.min(3, result.sessionIds.length); i++) {
        console.log(`   ${i + 1}. Session ID: ${result.sessionIds[i]}`);
      }
    } else {
      console.log(`❌ Error: ${result.errorMessage}`);
    }

    // Example 2: List sessions with specific label
    console.log("\n" + "=".repeat(60));
    console.log("Example 2: List sessions filtered by project label");
    console.log("=".repeat(60));

    const result2 = await agentBay.list({ project: "list-demo" });
    if (result2.success) {
      console.log(
        `✅ Found ${result2.totalCount} sessions with project='list-demo'`
      );
      console.log(`📄 Showing ${result2.sessionIds.length} session IDs on this page`);
      console.log(`🔑 Request ID: ${result2.requestId}`);

      for (let i = 0; i < result2.sessionIds.length; i++) {
        console.log(`   ${i + 1}. Session ID: ${result2.sessionIds[i]}`);
      }
    } else {
      console.log(`❌ Error: ${result2.errorMessage}`);
    }

    // Example 3: List sessions with multiple labels
    console.log("\n" + "=".repeat(60));
    console.log("Example 3: List sessions filtered by multiple labels");
    console.log("=".repeat(60));

    const result3 = await agentBay.list({
      project: "list-demo",
      environment: "dev",
    });
    if (result3.success) {
      console.log(
        `✅ Found ${result3.totalCount} sessions with project='list-demo' AND environment='dev'`
      );
      console.log(`📄 Showing ${result3.sessionIds.length} session IDs`);
      console.log(`🔑 Request ID: ${result3.requestId}`);

      for (let i = 0; i < result3.sessionIds.length; i++) {
        console.log(`   ${i + 1}. Session ID: ${result3.sessionIds[i]}`);
      }
    } else {
      console.log(`❌ Error: ${result3.errorMessage}`);
    }

    // Example 4: List sessions with pagination
    console.log("\n" + "=".repeat(60));
    console.log("Example 4: List sessions with pagination (2 per page)");
    console.log("=".repeat(60));

    // Get first page
    const resultPage1 = await agentBay.list({ project: "list-demo" }, 1, 2);
    if (resultPage1.success) {
      console.log(`📄 Page 1:`);
      console.log(`   Total count: ${resultPage1.totalCount}`);
      console.log(`   Session IDs on this page: ${resultPage1.sessionIds.length}`);
      console.log(`   Request ID: ${resultPage1.requestId}`);

      for (let i = 0; i < resultPage1.sessionIds.length; i++) {
        console.log(`   ${i + 1}. Session ID: ${resultPage1.sessionIds[i]}`);
      }

      // Get second page if available
      if (resultPage1.nextToken) {
        console.log(
          `\n   Has next page (token: ${resultPage1.nextToken.substring(0, 20)}...)`
        );

        const resultPage2 = await agentBay.list({ project: "list-demo" }, 2, 2);
        if (resultPage2.success) {
          console.log(`\n📄 Page 2:`);
          console.log(`   Session IDs on this page: ${resultPage2.sessionIds.length}`);
          console.log(`   Request ID: ${resultPage2.requestId}`);

          for (let i = 0; i < resultPage2.sessionIds.length; i++) {
            console.log(
              `   ${i + 1}. Session ID: ${resultPage2.sessionIds[i]}`
            );
          }
        }
      }
    } else {
      console.log(`❌ Error: ${resultPage1.errorMessage}`);
    }

    // Example 5: Retrieve all session IDs across multiple pages
    console.log("\n" + "=".repeat(60));
    console.log("Example 5: Retrieve all session IDs with pagination loop");
    console.log("=".repeat(60));

    const allSessionIds: string[] = [];
    let page = 1;
    const limit = 2;

    while (true) {
      const result = await agentBay.list({ owner: "demo-user" }, page, limit);

      if (!result.success) {
        console.log(`❌ Error on page ${page}: ${result.errorMessage}`);
        break;
      }

      console.log(`📄 Page ${page}: Found ${result.sessionIds.length} session IDs`);
      allSessionIds.push(...result.sessionIds);

      // Break if no more pages
      if (!result.nextToken) {
        break;
      }

      page++;
    }

    console.log(
      `\n✅ Retrieved ${allSessionIds.length} total session IDs across ${page} pages`
    );
    for (let i = 0; i < allSessionIds.length; i++) {
      console.log(`   ${i + 1}. Session ID: ${allSessionIds[i]}`);
    }
  } finally {
    // Clean up: Delete test sessions
    console.log("\n" + "=".repeat(60));
    console.log("🧹 Cleaning up test sessions...");
    console.log("=".repeat(60));

    for (const session of testSessions) {
      try {
        const deleteResult = await agentBay.delete(session);
        if (deleteResult.success) {
          console.log(`✅ Deleted session: ${session.sessionId}`);
          console.log(`   Request ID: ${deleteResult.requestId}`);
        } else {
          console.log(
            `❌ Failed to delete session ${session.sessionId}: ${deleteResult.errorMessage}`
          );
        }
      } catch (error) {
        console.error(
          `❌ Error deleting session ${session.sessionId}: ${error}`
        );
      }
    }
  }

  console.log("\n✨ Demo completed successfully!");
}

// Run the main function
main().catch((error) => {
  console.error("❌ Unhandled error:", error);
  process.exit(1);
});

