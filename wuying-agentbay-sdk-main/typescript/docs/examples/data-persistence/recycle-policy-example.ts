/**
 * RecyclePolicy Example - Data Lifecycle Management
 *
 * This example demonstrates how to use RecyclePolicy to control the lifecycle
 * of context data in the cloud.
 *
 * Expected Output:
 *
 * ======================================================================
 * Example 1: Default RecyclePolicy
 * ======================================================================
 * ✅ Context created: SdkCtx-xxxxxxxxxxxxx
 *    Lifecycle: Lifecycle_Forever
 *    Paths: [""]
 * ✅ Session created: session-xxxxxxxxxxxxx
 * ✅ Data written to /tmp/default_data/test.txt
 * ✅ Session deleted
 * ✅ Context deleted
 *
 * ======================================================================
 * Example 2: RecyclePolicy with 1 Day Lifecycle
 * ======================================================================
 * ✅ Context created: SdkCtx-xxxxxxxxxxxxx
 *    Lifecycle: Lifecycle_1Day
 *    Paths: [""]
 * ✅ Session created: session-xxxxxxxxxxxxx
 * ✅ Data written to /tmp/oneday_data/test.txt
 *    ℹ️  This data will be automatically deleted after 1 day
 * ✅ Session deleted
 * ✅ Context deleted
 *
 * ======================================================================
 * Example 3: RecyclePolicy for Specific Paths
 * ======================================================================
 * ✅ Context created: SdkCtx-xxxxxxxxxxxxx
 *    Lifecycle: Lifecycle_3Days
 *    Paths: ["/tmp/cache", "/tmp/logs"]
 *    ℹ️  Only files in /tmp/cache and /tmp/logs will be deleted after 3 days
 * ✅ Session created: session-xxxxxxxxxxxxx
 * ✅ Session deleted
 * ✅ Context deleted
 *
 * ======================================================================
 * Example 4: Different Lifecycle Options
 * ======================================================================
 * 📋 Available Lifecycle Options:
 * --------------------------------------------------
 *    Lifecycle_1Day            - 1 day
 *    Lifecycle_3Days           - 3 days
 *    Lifecycle_5Days           - 5 days
 *    Lifecycle_10Days          - 10 days
 *    Lifecycle_30Days          - 30 days
 *    Lifecycle_Forever         - Forever (permanent)
 * ✅ All lifecycle options validated successfully
 */

import { AgentBay } from "../../../src/agent-bay";
import { CreateSessionParams } from "../../../src/session-params";
import {
  ContextSync,
  Lifecycle,
  newRecyclePolicy,
  newSyncPolicy,
  RecyclePolicy,
  SyncPolicyImpl,
} from "../../../src/context-sync";

async function example1DefaultRecyclePolicy(): Promise<void> {
  console.log("\n" + "=".repeat(70));
  console.log("Example 1: Default RecyclePolicy");
  console.log("=".repeat(70));

  const agentBay = new AgentBay();

  // Create a context
  const contextResult = await agentBay.context.get("default-recycle-demo", {
    create: true,
  });
  if (!contextResult.success || !contextResult.context) {
    console.log(`❌ Failed to create context: ${contextResult.errorMessage}`);
    return;
  }

  const context = contextResult.context;
  console.log(`✅ Context created: ${context.id}`);

  // Use default SyncPolicy (includes default RecyclePolicy with Lifecycle_Forever)
  const syncPolicy = newSyncPolicy();
  console.log(`   Lifecycle: ${syncPolicy.recyclePolicy?.lifecycle}`);
  console.log(`   Paths: ${JSON.stringify(syncPolicy.recyclePolicy?.paths)}`);

  const contextSync = new ContextSync(context.id, "/tmp/default_data", syncPolicy);

  // Create session with context sync
  const params = new CreateSessionParams();
  params.contextSyncs = [contextSync];
  const sessionResult = await agentBay.create(params);

  if (!sessionResult.success || !sessionResult.session) {
    console.log(`❌ Failed to create session: ${sessionResult.errorMessage}`);
    return;
  }

  const session = sessionResult.session;
  console.log(`✅ Session created: ${session.sessionId}`);

  // Write some data
  await session.command.executeCommand(
    "echo 'Default policy - data kept forever' > /tmp/default_data/test.txt"
  );
  console.log("✅ Data written to /tmp/default_data/test.txt");

  // Clean up
  await agentBay.delete(session);
  console.log("✅ Session deleted");

  await agentBay.context.delete(context);
  console.log("✅ Context deleted");
}

async function example2OneDayLifecycle(): Promise<void> {
  console.log("\n" + "=".repeat(70));
  console.log("Example 2: RecyclePolicy with 1 Day Lifecycle");
  console.log("=".repeat(70));

  const agentBay = new AgentBay();

  // Create a context
  const contextResult = await agentBay.context.get("one-day-recycle-demo", {
    create: true,
  });
  if (!contextResult.success || !contextResult.context) {
    console.log(`❌ Failed to create context: ${contextResult.errorMessage}`);
    return;
  }

  const context = contextResult.context;
  console.log(`✅ Context created: ${context.id}`);

  // Create custom RecyclePolicy with 1 day lifecycle
  const recyclePolicy: RecyclePolicy = {
    lifecycle: Lifecycle.Lifecycle_1Day,
    paths: [""], // Apply to all paths
  };

  // Create SyncPolicy with custom RecyclePolicy
  const syncPolicy = new SyncPolicyImpl({
    recyclePolicy: recyclePolicy,
  });

  console.log(`   Lifecycle: ${syncPolicy.recyclePolicy?.lifecycle}`);
  console.log(`   Paths: ${JSON.stringify(syncPolicy.recyclePolicy?.paths)}`);

  const contextSync = new ContextSync(context.id, "/tmp/oneday_data", syncPolicy);

  // Create session with context sync
  const params = new CreateSessionParams();
  params.labels = { example: "recycle_policy", lifecycle: "1day" };
  params.contextSyncs = [contextSync];
  const sessionResult = await agentBay.create(params);

  if (!sessionResult.success || !sessionResult.session) {
    console.log(`❌ Failed to create session: ${sessionResult.errorMessage}`);
    return;
  }

  const session = sessionResult.session;
  console.log(`✅ Session created: ${session.sessionId}`);

  // Write some data
  await session.command.executeCommand("mkdir -p /tmp/oneday_data");
  await session.command.executeCommand(
    "echo 'This data will be deleted after 1 day' > /tmp/oneday_data/test.txt"
  );
  console.log("✅ Data written to /tmp/oneday_data/test.txt");
  console.log("   ℹ️  This data will be automatically deleted after 1 day");

  // Clean up
  await agentBay.delete(session);
  console.log("✅ Session deleted");

  await agentBay.context.delete(context);
  console.log("✅ Context deleted");
}

async function example3SpecificPaths(): Promise<void> {
  console.log("\n" + "=".repeat(70));
  console.log("Example 3: RecyclePolicy for Specific Paths");
  console.log("=".repeat(70));

  const agentBay = new AgentBay();

  // Create a context
  const contextResult = await agentBay.context.get("specific-path-demo", {
    create: true,
  });
  if (!contextResult.success || !contextResult.context) {
    console.log(`❌ Failed to create context: ${contextResult.errorMessage}`);
    return;
  }

  const context = contextResult.context;
  console.log(`✅ Context created: ${context.id}`);

  // Create RecyclePolicy for specific paths
  const recyclePolicy: RecyclePolicy = {
    lifecycle: Lifecycle.Lifecycle_3Days,
    paths: ["/tmp/cache", "/tmp/logs"], // Only these paths
  };

  const syncPolicy = new SyncPolicyImpl({ recyclePolicy: recyclePolicy });

  console.log(`   Lifecycle: ${syncPolicy.recyclePolicy?.lifecycle}`);
  console.log(`   Paths: ${JSON.stringify(syncPolicy.recyclePolicy?.paths)}`);
  console.log(
    "   ℹ️  Only files in /tmp/cache and /tmp/logs will be deleted after 3 days"
  );

  const contextSync = new ContextSync(
    context.id,
    "/tmp/multipath_data",
    syncPolicy
  );

  // Create session
  const params = new CreateSessionParams();
  params.contextSyncs = [contextSync];
  const sessionResult = await agentBay.create(params);

  if (!sessionResult.success || !sessionResult.session) {
    console.log(`❌ Failed to create session: ${sessionResult.errorMessage}`);
    return;
  }

  const session = sessionResult.session;
  console.log(`✅ Session created: ${session.sessionId}`);

  // Clean up
  await agentBay.delete(session);
  console.log("✅ Session deleted");

  await agentBay.context.delete(context);
  console.log("✅ Context deleted");
}

function example4DifferentLifecycles(): void {
  console.log("\n" + "=".repeat(70));
  console.log("Example 4: Different Lifecycle Options");
  console.log("=".repeat(70));

  const lifecycles = [
    { lifecycle: Lifecycle.Lifecycle_1Day, description: "1 day" },
    { lifecycle: Lifecycle.Lifecycle_3Days, description: "3 days" },
    { lifecycle: Lifecycle.Lifecycle_5Days, description: "5 days" },
    { lifecycle: Lifecycle.Lifecycle_10Days, description: "10 days" },
    { lifecycle: Lifecycle.Lifecycle_30Days, description: "30 days" },
    { lifecycle: Lifecycle.Lifecycle_Forever, description: "Forever (permanent)" },
  ];

  console.log("\n📋 Available Lifecycle Options:");
  console.log("-".repeat(50));
  for (const { lifecycle, description} of lifecycles) {
    const recyclePolicy: RecyclePolicy = {
      lifecycle: lifecycle,
      paths: [""],
    };
    console.log(`   ${lifecycle.padEnd(25)} - ${description}`);
  }

  console.log("\n✅ All lifecycle options validated successfully");
}

async function main(): Promise<void> {
  console.log("\n" + "=".repeat(70));
  console.log("RecyclePolicy Examples - Data Lifecycle Management");
  console.log("=".repeat(70));
  console.log("\nThese examples demonstrate how to use RecyclePolicy to control");
  console.log("the lifecycle of context data in the cloud.");

  try {
    // Run examples
    await example1DefaultRecyclePolicy();
    await example2OneDayLifecycle();
    await example3SpecificPaths();
    example4DifferentLifecycles();

    console.log("\n" + "=".repeat(70));
    console.log("✅ All RecyclePolicy examples completed successfully!");
    console.log("=".repeat(70));
  } catch (error) {
    console.log(`\n❌ Example failed with error: ${error}`);
    console.error(error);
  }
}

// Only run if this file is executed directly
if (require.main === module) {
  main();
}

