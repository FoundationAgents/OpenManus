import { AgentBay, ContextSync, CreateSessionParams, newSyncPolicyWithDefaults } from "../../../src";

/**
 * Context Sync Dual-Mode Example for TypeScript SDK
 * 
 * This example demonstrates the dual-mode context.sync() functionality:
 * 1. Async mode with callback - immediate return, result handled via callback
 * 2. Sync mode with await - waits for completion before returning
 */

async function contextSyncWithCallbackDemo(agentBay: AgentBay): Promise<void> {
  console.log("🔄 Starting context sync with callback demo...");
  
  // Step 1: Create context for persistent storage
  console.log("\n📦 Creating context for persistent storage...");
  const contextResult = await agentBay.context.get("sync-callback-demo", true);
  if (!contextResult.success) {
    throw new Error(`Context creation failed: ${contextResult.errorMessage}`);
  }
  const context = contextResult.context!;
  console.log(`✅ Context created: ${context.id}`);
  
  // Step 2: Create session with context sync
  console.log("\n📦 Creating session with context sync...");
  const syncPolicy = newSyncPolicyWithDefaults();
  const contextSync = new ContextSync(
    context.id,
    "/tmp/sync_data",
    syncPolicy
  );
  
  const params: CreateSessionParams = {
    contextSync: [contextSync]
  };
  const sessionResult = await agentBay.create(params);
  if (!sessionResult.success) {
    throw new Error(`Failed to create session: ${sessionResult.errorMessage}`);
  }
  const session = sessionResult.session!;
  console.log(`✅ Session created: ${session.getSessionId()}`);
  
  // Step 3: Create test data
  console.log("\n💾 Creating test data...");
  await session.command.executeCommand("mkdir -p /tmp/sync_data/test_files");
  
  const testFiles = [
    {
      path: "/tmp/sync_data/test_files/small.txt",
      content: "Small test file content\n".repeat(10)
    },
    {
      path: "/tmp/sync_data/test_files/medium.txt", 
      content: "Medium test file content\n".repeat(100)
    },
    {
      path: "/tmp/sync_data/config.json",
      content: JSON.stringify({
        sync_demo: true,
        created_at: new Date().toISOString(),
        session_id: session.getSessionId()
      }, null, 2)
    }
  ];
  
  let createdFiles = 0;
  for (const file of testFiles) {
    const writeResult = await session.fileSystem.writeFile(file.path, file.content);
    if (writeResult.success) {
      console.log(`✅ Created file: ${file.path}`);
      createdFiles++;
    } else {
      console.log(`❌ Failed to create file ${file.path}: ${writeResult.errorMessage}`);
    }
  }
  
  console.log(`📊 Created ${createdFiles}/${testFiles.length} test files`);
  
  try {
    // Method 1: Async interface with callback
    console.log("\n📞 Calling context.sync() with callback...");
    const syncStartTime = Date.now();
    
    // Use callback mode - function returns immediately
    const syncResult = await session.context.sync(
      undefined, // contextId
      undefined, // path  
      undefined, // mode
      (success: boolean) => {
        console.log("Callback called ==============");
        const callbackTime = Date.now();
        const duration = callbackTime - syncStartTime;
        
        if (success) {
          console.log(`✅ Context sync completed successfully in ${duration}ms`);
        } else {
          console.log(`❌ Context sync completed with failures in ${duration}ms`);
        }
        
        // Delete session in callback
        console.log("🗑️  Deleting session from callback...");
        session.delete(false) // Don't sync again since we already did
          .then(() => {
            console.log("✅ Session deleted successfully from callback");
          })
          .catch((error: any) => {
            console.error("❌ Failed to delete session from callback:", error);
          });
      }
    );
    
    console.log(`📤 Sync initiation result: success=${syncResult.success}, requestId=${syncResult.requestId}`);
    console.log("⏳ Waiting for callback to complete...");
    
    // Wait a bit for the callback to complete
    await new Promise(resolve => setTimeout(resolve, 10000));
    
  } catch (error) {
    console.error("❌ Context sync with callback failed:", error);
    // Clean up session
    try {
      await session.delete(false);
      console.log("✅ Session cleaned up after error");
    } catch (deleteError) {
      console.error("❌ Failed to clean up session:", deleteError);
    }
  }
}

async function contextSyncDemo(agentBay: AgentBay): Promise<void> {
  console.log("🔄 Starting context sync demo...");
  
  // Step 1: Create context for persistent storage
  console.log("\n📦 Creating context for persistent storage...");
  const contextResult = await agentBay.context.get("sync-await-demo", true);
  if (!contextResult.success) {
    throw new Error(`Context creation failed: ${contextResult.errorMessage}`);
  }
  const context = contextResult.context!;
  console.log(`✅ Context created: ${context.id}`);
  
  // Step 2: Create session with context sync
  console.log("\n📦 Creating session with context sync...");
  const syncPolicy = newSyncPolicyWithDefaults();
  const contextSync = new ContextSync(
    context.id,
    "/tmp/sync_data",
    syncPolicy
  );
  
  const params: CreateSessionParams = {
    contextSync: [contextSync]
  };
  const sessionResult = await agentBay.create(params);
  if (!sessionResult.success) {
    throw new Error(`Failed to create session: ${sessionResult.errorMessage}`);
  }
  const session = sessionResult.session!;
  console.log(`✅ Session created: ${session.getSessionId()}`);
  
  // Step 3: Create test data
  console.log("\n💾 Creating test data...");
  await session.command.executeCommand("mkdir -p /tmp/sync_data/test_files");
  
  const testFiles = [
    {
      path: "/tmp/sync_data/test_files/small.txt",
      content: "Small test file content\n".repeat(10)
    },
    {
      path: "/tmp/sync_data/test_files/medium.txt", 
      content: "Medium test file content\n".repeat(100)
    },
    {
      path: "/tmp/sync_data/config.json",
      content: JSON.stringify({
        sync_demo: true,
        created_at: new Date().toISOString(),
        session_id: session.getSessionId()
      }, null, 2)
    }
  ];
  
  let createdFiles = 0;
  for (const file of testFiles) {
    const writeResult = await session.fileSystem.writeFile(file.path, file.content);
    if (writeResult.success) {
      console.log(`✅ Created file: ${file.path}`);
      createdFiles++;
    } else {
      console.log(`❌ Failed to create file ${file.path}: ${writeResult.errorMessage}`);
    }
  }
  
  console.log(`📊 Created ${createdFiles}/${testFiles.length} test files`);
  
  try {
    // Method 2: Sync interface with await
    console.log("\n⏳ Calling context.sync() with await...");
    const syncStartTime = Date.now();
    
    // Use await mode - function waits for completion
    const syncResult = await session.context.sync();
    
    const syncDuration = Date.now() - syncStartTime;
    
    if (syncResult.success) {
      console.log(`✅ Context sync completed successfully in ${syncDuration}ms`);
    } else {
      console.log(`❌ Context sync completed with failures in ${syncDuration}ms`);
    }
    
    console.log(`📤 Sync result: success=${syncResult.success}, requestId=${syncResult.requestId}`);
    
    // Delete session
    console.log("🗑️  Deleting session...");
    await session.delete(false); // Don't sync again since we already did
    console.log("✅ Session deleted successfully");
    
  } catch (error) {
    console.error("❌ Context sync failed:", error);
    // Clean up session
    try {
      await session.delete(false);
      console.log("✅ Session cleaned up after error");
    } catch (deleteError) {
      console.error("❌ Failed to clean up session:", deleteError);
    }
  }
}

async function main(): Promise<void> {
  console.log("🔄 AgentBay Context Sync Dual-Mode Example (TypeScript)");
  
  // Initialize AgentBay client
  const agentBay = new AgentBay();
  
  try {
    // Method 1: Async interface with callback
    console.log("\n" + "=".repeat(60));
    console.log("🔄 Method 1: context_sync_with_callback (Async with callback)");
    console.log("=".repeat(60));
    
    // Start the first demo without waiting for it to complete
    const callbackPromise = contextSyncWithCallbackDemo(agentBay);
    console.log("contextSyncWithCallbackDemo started (not awaited)");
    console.log("=".repeat(60));
    
    // Sleep 3 seconds
    console.log("\n⏳ Sleeping 3 seconds before next demo...");
    await new Promise(resolve => setTimeout(resolve, 3000));
    
    // Method 2: Sync interface with await
    console.log("\n" + "=".repeat(60));
    console.log("🔄 Method 2: context_sync (Sync with await)");
    console.log("=".repeat(60));
    await contextSyncDemo(agentBay); // With await
    
    // Wait for the first demo to complete
    console.log("\n⏳ Waiting for callback demo to complete...");
    await callbackPromise;
    
  } catch (error) {
    console.error("❌ Example execution failed:", error);
  }
  
  console.log("✅ Context sync dual-mode example completed");
}

// Run the example
if (require.main === module) {
  main().catch(console.error);
}

export { contextSyncDemo, contextSyncWithCallbackDemo, main };

