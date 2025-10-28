import { AgentBay } from "../../src";
import { Session } from "../../src/session";
import { FileChangeEvent } from "../../src/filesystem/filesystem";
import { getTestApiKey } from "../utils/test-helpers";

describe("FileSystem Watch Directory Integration Tests", () => {
  let agentBay: AgentBay;
  let session: Session;

  beforeAll(async () => {
    // Skip if no API key
    const apiKey = getTestApiKey();
    if (!apiKey) {
      console.log("Skipping integration test: AGENTBAY_API_KEY environment variable not set");
      return;
    }

    console.log("=== Testing watch_directory functionality ===");

    // Initialize AgentBay client
    agentBay = new AgentBay({ apiKey });
    expect(agentBay).toBeDefined();
    console.log("✅ AgentBay client initialized");

    // Create session with code_latest ImageId
    const sessionResult = await agentBay.create({
      imageId: "code_latest"
    });
    expect(sessionResult.success).toBe(true);
    expect(sessionResult.session).toBeDefined();

    session = sessionResult.session!;
    console.log(`✅ Session created successfully with ID: ${session.sessionId}`);
  });

  afterAll(async () => {
    if (session && agentBay) {
      console.log("\n7. Cleaning up session...");
      const deleteResult = await agentBay.delete(session);
      if (deleteResult.success) {
        console.log("✅ Session deleted successfully");
      } else {
        console.log(`❌ Failed to delete session: ${deleteResult.errorMessage}`);
      }
    }
  });

  it("should detect exactly 5 events from 3 writeFile operations", async () => {
    const apiKey = getTestApiKey();
    if (!apiKey) {
      console.log("Skipping test: AGENTBAY_API_KEY not set");
      return;
    }

    const testDir = "/tmp/watch_test_integration_ts";

    // Create the test directory
    console.log(`\n1. Creating test directory: ${testDir}`);
    const createDirResult = await session.fileSystem.createDirectory(testDir);
    expect(createDirResult.success).toBe(true);
    console.log("✅ Test directory created");

    // Storage for detected events
    const detectedEvents: FileChangeEvent[] = [];
    const callbackCalls: number[] = [];

    const fileChangeCallback = (events: FileChangeEvent[]) => {
      callbackCalls.push(events.length);
      detectedEvents.push(...events);
      console.log(`\n🔔 Callback triggered with ${events.length} events:`);
      for (const event of events) {
        console.log(`   - ${event.eventType}: ${event.path} (${event.pathType})`);
      }
    };

    // Start directory monitoring
    console.log("\n2. Starting directory monitoring...");
    
    // Create a simple stop mechanism
    let shouldStop = false;
    const stopSignal = {
      get aborted() { return shouldStop; },
      addEventListener: (_type: string, _listener: any) => { /* no-op */ },
      removeEventListener: (_type: string, _listener: any) => { /* no-op */ },
      dispatchEvent: (_event: any) => false,
      onabort: null,
      reason: undefined,
      throwIfAborted: () => { /* no-op */ }
    } as AbortSignal;
    
    const watchPromise = session.fileSystem.watchDirectory(
      testDir,
      fileChangeCallback,
      500, // Poll every 0.5 seconds for faster testing
      stopSignal
    );
    console.log("✅ Directory monitoring started");

    // Wait a moment for monitoring to initialize
    await new Promise(resolve => setTimeout(resolve, 1000));

    try {
      // Test 1: Create a new file
      console.log("\n3. Creating a new file...");
      const writeResult = await session.fileSystem.writeFile(`${testDir}/test1.txt`, "Initial content");
      console.log(`Write file result: ${writeResult.success}`);
      expect(writeResult.success).toBe(true);

      // Wait for detection
      await new Promise(resolve => setTimeout(resolve, 2000));

      // Test 2: Modify the file
      console.log("\n4. Modifying the file...");
      const modifyResult = await session.fileSystem.writeFile(`${testDir}/test1.txt`, "Modified content");
      console.log(`Modify file result: ${modifyResult.success}`);
      expect(modifyResult.success).toBe(true);

      // Wait for detection
      await new Promise(resolve => setTimeout(resolve, 2000));

      // Test 3: Create another file
      console.log("\n5. Creating another file...");
      const writeResult2 = await session.fileSystem.writeFile(`${testDir}/test2.txt`, "Second file content");
      console.log(`Write second file result: ${writeResult2.success}`);
      expect(writeResult2.success).toBe(true);

      // Wait for detection
      await new Promise(resolve => setTimeout(resolve, 2000));

    } finally {
      // Stop monitoring
      console.log("\n6. Stopping directory monitoring...");
      shouldStop = true;
      await watchPromise;
      console.log("✅ Directory monitoring stopped");
    }

    // Analyze results
    console.log("\n=== RESULTS ===");
    console.log(`Total callback calls: ${callbackCalls.length}`);
    console.log(`Total events detected: ${detectedEvents.length}`);
    console.log(`Callback call sizes: [${callbackCalls.join(", ")}]`);

    console.log("\nDetected events:");
    for (let i = 0; i < detectedEvents.length; i++) {
      console.log(`  ${i + 1}. ${detectedEvents[i].eventType}: ${detectedEvents[i].path} (${detectedEvents[i].pathType})`);
    }

    // Verify exact number of events - must be exactly 5
    // writeFile to non-existent file produces: create + modify (2 events)
    // writeFile to existing file produces: modify (1 event)
    // Expected: test1.txt creation (create+modify) + test1.txt modification (modify) + test2.txt creation (create+modify) = 5 events
    const expectedEvents = 5;
    if (detectedEvents.length !== expectedEvents) {
      console.log(`❌ Expected exactly ${expectedEvents} events, got ${detectedEvents.length}`);
      console.log("Expected breakdown:");
      console.log("  - writeFile test1.txt (new): create + modify = 2 events");
      console.log("  - writeFile test1.txt (existing): modify = 1 event");
      console.log("  - writeFile test2.txt (new): create + modify = 2 events");
      console.log("  - Total: 2 + 1 + 2 = 5 events");
    } else {
      console.log(`✅ Captured expected number of events: ${detectedEvents.length}`);
    }

    expect(detectedEvents.length).toBe(expectedEvents);

    // Verify event types and counts
    const createEvents = detectedEvents.filter(event => event.eventType === "create").length;
    const modifyEvents = detectedEvents.filter(event => event.eventType === "modify").length;

    console.log("\nEvent type breakdown:");
    console.log(`  Create events: ${createEvents} (expected: 2)`);
    console.log(`  Modify events: ${modifyEvents} (expected: 3)`);

    // Strict validation of event types
    const expectedCreateEvents = 2;
    const expectedModifyEvents = 3;

    expect(createEvents).toBe(expectedCreateEvents);
    expect(modifyEvents).toBe(expectedModifyEvents);
    expect(detectedEvents.length).toBe(expectedEvents);

    if (createEvents === expectedCreateEvents && modifyEvents === expectedModifyEvents) {
      console.log("✅ Event type distribution is correct");
    } else {
      console.log("❌ Event type distribution is incorrect");
      throw new Error(`Event type validation failed: got ${createEvents} create + ${modifyEvents} modify, expected ${expectedCreateEvents} create + ${expectedModifyEvents} modify`);
    }

    // Verify deduplication
    const eventKeys = new Set<string>();
    let duplicates = 0;
    for (const event of detectedEvents) {
      const eventKey = `${event.eventType}:${event.path}:${event.pathType}`;
      if (eventKeys.has(eventKey)) {
        duplicates++;
      } else {
        eventKeys.add(eventKey);
      }
    }

    console.log("\nDeduplication check:");
    console.log(`  Unique events: ${eventKeys.size}`);
    console.log(`  Duplicate events: ${duplicates}`);

    if (duplicates === 0) {
      console.log("✅ Event deduplication is working correctly");
    } else {
      console.log("⚠️  Some duplicate events were detected");
    }

    // Summary
    if (detectedEvents.length === expectedEvents && createEvents === expectedCreateEvents && modifyEvents === expectedModifyEvents) {
      console.log("\n✅ watch_directory integration test completed successfully!");
      console.log("All expected events were detected with correct types.");
    } else {
      console.log("\n❌ watch_directory integration test failed!");
      console.log(`Expected ${expectedEvents} events (${expectedCreateEvents} create + ${expectedModifyEvents} modify), got ${detectedEvents.length} events (${createEvents} create + ${modifyEvents} modify)`);
      throw new Error("Integration test validation failed");
    }
  });
}); 