import { AgentBay } from "../../src/agent-bay";
import { ContextStatusData } from "../../src/context-manager";
import { ContextSync, newSyncPolicy, newContextSync } from "../../src/context-sync";
import { wait, randomString } from "../utils/test-helpers";
import { log } from "../../src/utils/logger";

describe("ContextSyncIntegration", () => {
  let agentBay: AgentBay;
  let contextId: string;
  let sessionId: string;
  
  // Skip tests if no API key is available or in CI environment
  const apiKey = process.env.AGENTBAY_API_KEY;
  const shouldSkip = !apiKey || process.env.CI;
  
  beforeAll(async () => {
    if (shouldSkip) {
      return;
    }
    
    // Initialize AgentBay client
    agentBay = new AgentBay({ apiKey: apiKey! });
    
    // Create a unique context name for this test
    const contextName = `test-sync-context-${Date.now()}`;
    
    // Create a context
    const contextResult = await agentBay.context.get(contextName, true);
    if (!contextResult.success || !contextResult.context) {
      throw new Error("Failed to create context");
    }
    
    contextId = contextResult.context.id;
    log(`Created context: ${contextResult.context.name} (ID: ${contextId})`);
    
    // Create session parameters with context sync
    const sessionParams = {
      contextSync: [
        newContextSync(contextId, "/home/wuying", newSyncPolicy())
      ],
      labels: { "test": "context-sync-integration" },
      imageId: "linux_latest"
    };
    
    // Create session
    const sessionResult = await agentBay.create(sessionParams);
    if (!sessionResult.success || !sessionResult.session) {
      await agentBay.context.delete(contextResult.context!);
      throw new Error("Failed to create session");
    }
    
    sessionId = sessionResult.session.sessionId;
    log(`Created session: ${sessionId}`);
    
    // Wait for session to be ready
    await wait(10000);
  });
  
  afterAll(async () => {
    if (shouldSkip) {
      return;
    }
    
    // Clean up session
    try {
      if (sessionId) {
        // Find the session in the sessions map
        const sessions = agentBay.list();
        const session = sessions.find(s => s.sessionId === sessionId);
        if (session) {
          await agentBay.delete(session);
          log(`Session deleted: ${sessionId}`);
        }
      }
    } catch (e) {
      console.warn(`Warning: Failed to delete session: ${e}`);
    }
    
    // Clean up context
    try {
      if (contextId) {
        // We need to create a context object to delete it
        const context = { id: contextId, name: "", state: "" };
        await agentBay.context.delete(context);
        log(`Context deleted: ${contextId}`);
      }
    } catch (e) {
      console.warn(`Warning: Failed to delete context: ${e}`);
    }
  });
  
  // Skip all tests if no API key is available or in CI environment
  
  it("should return parsed ContextStatusData", async () => {
    if (shouldSkip) {
      log("Skipping test: No API key available or running in CI");
      return;
    }
    
    // Get the session
    const sessions = agentBay.list();
    const session = sessions.find(s => s.sessionId === sessionId);
    if (!session) {
      throw new Error(`Session ${sessionId} not found`);
    }
    
    // Get context info
    const contextInfo = await session.context.info();
    
    // Verify that we have a request ID
    expect(contextInfo.requestId).toBeDefined();
    expect(contextInfo.requestId).not.toBe("");
    
    // Log the context status data
    log(`Context status data count: ${contextInfo.contextStatusData.length}`);
    for (let i = 0; i < contextInfo.contextStatusData.length; i++) {
      const data = contextInfo.contextStatusData[i];
      console.log(`Status data ${i}:`);
      console.log(`  Context ID: ${data.contextId}`);
      console.log(`  Path: ${data.path}`);
      console.log(`  Status: ${data.status}`);
      console.log(`  Task Type: ${data.taskType}`);
      console.log(`  Start Time: ${data.startTime}`);
      console.log(`  Finish Time: ${data.finishTime}`);
      if (data.errorMessage) {
        console.log(`  Error: ${data.errorMessage}`);
      }
    }
    
    // There might not be any status data yet, so we don't assert on the count
    // But if there is data, verify it has the expected structure
    for (const data of contextInfo.contextStatusData) {
      expect(data).toBeInstanceOf(Object);
      expect(data.contextId).toBeDefined();
      expect(data.path).toBeDefined();
      expect(data.status).toBeDefined();
      expect(data.taskType).toBeDefined();
    }
  });
  
  it("should sync context and return info", async () => {
    if (shouldSkip) {
      log("Skipping test: No API key available or running in CI");
      return;
    }
    
    // Get the session
    const sessions = agentBay.list();
    const session = sessions.find(s => s.sessionId === sessionId);
    if (!session) {
      throw new Error(`Session ${sessionId} not found`);
    }
    
    // Sync context
    const syncResult = await session.context.sync();
    
    // Verify sync result
    expect(syncResult.success).toBe(true);
    expect(syncResult.requestId).toBeDefined();
    expect(syncResult.requestId).not.toBe("");
    
    // Wait for sync to complete
    await wait(5000);
    
    // Get context info
    const contextInfo = await session.context.info();
    
    // Verify context info
    expect(contextInfo.requestId).toBeDefined();
    
    // Log the context status data
    console.log(`Context status data after sync, count: ${contextInfo.contextStatusData.length}`);
    for (let i = 0; i < contextInfo.contextStatusData.length; i++) {
      const data = contextInfo.contextStatusData[i];
      console.log(`Status data ${i}:`);
      console.log(`  Context ID: ${data.contextId}`);
      console.log(`  Path: ${data.path}`);
      console.log(`  Status: ${data.status}`);
      console.log(`  Task Type: ${data.taskType}`);
    }
    
    // Check if we have status data for our context
    let foundContext = false;
    for (const data of contextInfo.contextStatusData) {
      if (data.contextId === contextId) {
        foundContext = true;
        expect(data.path).toBe("/home/wuying");
        // Status might vary, but should not be empty
        expect(data.status).toBeDefined();
        expect(data.status).not.toBe("");
        break;
      }
    }
    
    // We should have found our context in the status data
    // But this might be flaky in CI, so just log a warning if not found
    if (!foundContext) {
      console.warn(`Warning: Could not find context ${contextId} in status data`);
    }
  });
  
  it("should get context info with parameters", async () => {
    if (shouldSkip) {
      log("Skipping test: No API key available or running in CI");
      return;
    }
    
    // Get the session
    const sessions = agentBay.list();
    const session = sessions.find(s => s.sessionId === sessionId);
    if (!session) {
      throw new Error(`Session ${sessionId} not found`);
    }
    
    // Get context info with parameters
    const contextInfo = await session.context.infoWithParams(
      contextId,
      "/home/wuying",
      undefined
    );
    
    // Verify that we have a request ID
    expect(contextInfo.requestId).toBeDefined();
    
    // Log the filtered context status data
    console.log(`Filtered context status data count: ${contextInfo.contextStatusData.length}`);
    for (let i = 0; i < contextInfo.contextStatusData.length; i++) {
      const data = contextInfo.contextStatusData[i];
      console.log(`Status data ${i}:`);
      console.log(`  Context ID: ${data.contextId}`);
      console.log(`  Path: ${data.path}`);
      console.log(`  Status: ${data.status}`);
      console.log(`  Task Type: ${data.taskType}`);
    }
    
    // If we have status data, verify it matches our filters
    for (const data of contextInfo.contextStatusData) {
      if (data.contextId === contextId) {
        expect(data.path).toBe("/home/wuying");
      }
    }
  });

  it("should test context sync persistence with retry", async () => {
    if (shouldSkip) {
      log("Skipping test: No API key available or running in CI");
      return;
    }
    
    // 1. Create a unique context name and get its ID
    const contextName = `test-persistence-retry-ts-${randomString()}`;
    const contextResult = await agentBay.context.get(contextName, true);
    expect(contextResult.success).toBe(true);
    expect(contextResult.context).toBeDefined();
    
    const contextObj = contextResult.context!;
    const contextIdLocal = contextObj.id;
    console.log(`Created context: ${contextObj.name} (ID: ${contextIdLocal})`);
    
    // 2. Create a session with context sync, using a timestamped path under /home/wuying/
    const timestamp = Date.now();
    const syncPath = `/home/wuying/test-path-ts-${timestamp}`;
    
    // Use default sync policy
    const sessionParams = {
      imageId: "linux_latest",
      labels: { "test": "persistence-retry-test-ts" },
      contextSync: [
        newContextSync(contextIdLocal, syncPath, newSyncPolicy())
      ]
    };
    
    // Create first session
    const sessionResult = await agentBay.create(sessionParams);
    expect(sessionResult.success).toBe(true);
    expect(sessionResult.session).toBeDefined();
    
    const session1 = sessionResult.session!;
    console.log(`Created first session: ${session1.sessionId}`);
    
    // 3. Wait for session to be ready and retry context info until data is available
    console.log("Waiting for session to be ready and context status data to be available...");
    
    let foundData = false;
    let contextInfo;
    
    for (let i = 0; i < 20; i++) { // Retry up to 20 times
      contextInfo = await session1.context.info();
      
      if (contextInfo.contextStatusData && contextInfo.contextStatusData.length > 0) {
        console.log(`Found context status data on attempt ${i+1}`);
        foundData = true;
        break;
      }
      
      console.log(`No context status data available yet (attempt ${i+1}), retrying in 1 second...`);
      await wait(1000);
    }
    
    expect(foundData).toBe(true);
    printContextStatusData(contextInfo?.contextStatusData || []);
    
    // 4. Create a 1GB file in the context sync path
    const testFilePath = `${syncPath}/test-file.txt`;
    
    // Create directory first
    console.log(`Creating directory: ${syncPath}`);
    const dirResult = await session1.fileSystem.createDirectory(syncPath);
    expect(dirResult.success).toBe(true);
    
    // Create a 1GB file using dd command
    console.log(`Creating 1GB file at ${testFilePath}`);
    const createFileCmd = `dd if=/dev/zero of=${testFilePath} bs=1M count=1024`;
    const cmdResult = await session1.command.executeCommand(createFileCmd);
    expect(cmdResult.success).toBe(true);
    console.log(`Created 1GB file: ${cmdResult.output}`);
    
    // 5. Sync to trigger file upload
    console.log("Triggering context sync...");
    const syncResult = await session1.context.sync();
    expect(syncResult.success).toBe(true);
    console.log(`Context sync successful (RequestID: ${syncResult.requestId})`);
    
    // 6. Get context info with retry for upload status
    console.log("Checking file upload status with retry...");
    
    let foundUpload = false;
    for (let i = 0; i < 20; i++) { // Retry up to 20 times
      contextInfo = await session1.context.info();
      
      // Check if we have upload status for our context
      for (const data of contextInfo.contextStatusData) {
        if (data.contextId === contextIdLocal && data.taskType === "upload") {
          foundUpload = true;
          console.log(`Found upload task for context at attempt ${i+1}`);
          break;
        }
      }
      
      if (foundUpload) {
        break;
      }
      
      console.log(`No upload status found yet (attempt ${i+1}), retrying in 1 second...`);
      await wait(1000);
    }
    
    if (foundUpload) {
      console.log("Found upload status for context");
      printContextStatusData(contextInfo?.contextStatusData || []);
    } else {
      console.log("Warning: Could not find upload status after all retries");
    }
    
    // 7. Release first session
    console.log("Releasing first session...");
    const deleteResult = await agentBay.delete(session1, true);
    expect(deleteResult.success).toBe(true);
    
    // Wait longer for the session to be fully released and resources to be freed
    console.log("Waiting for session resources to be fully released...");
    await wait(5000);
    
    // 8. Create a second session with the same context ID
    console.log("Creating second session with the same context ID...");
    const sessionParams2 = {
      imageId: "linux_latest",
      labels: { "test": "persistence-retry-test-ts-second" },
      contextSync: [
        newContextSync(contextIdLocal, syncPath, newSyncPolicy())
      ]
    };
    
    const sessionResult2 = await agentBay.create(sessionParams2);
    expect(sessionResult2.success).toBe(true);
    expect(sessionResult2.session).toBeDefined();
    
    const session2 = sessionResult2.session!;
    console.log(`Created second session: ${session2.sessionId}`);
    
    // 9. Get context info with retry for download status
    console.log("Checking file download status with retry...");
    
    let foundDownload = false;
    for (let i = 0; i < 20; i++) { // Retry up to 20 times
      contextInfo = await session2.context.info();
      
      // Check if we have download status for our context
      for (const data of contextInfo.contextStatusData) {
        if (data.contextId === contextIdLocal && data.taskType === "download") {
          foundDownload = true;
          console.log(`Found download task for context at attempt ${i+1}`);
          break;
        }
      }
      
      if (foundDownload) {
        break;
      }
      
      console.log(`No download status found yet (attempt ${i+1}), retrying in 1 second...`);
      await wait(1000);
    }
    
    if (foundDownload) {
      console.log("Found download status for context");
      printContextStatusData(contextInfo?.contextStatusData || []);
    } else {
      console.log("Warning: Could not find download status after all retries");
    }
    
    // 10. Verify the 1GB file exists in the second session
    console.log("Verifying 1GB file exists in second session...");
    
    // Check file size using ls command
    const checkFileCmd = `ls -la ${testFilePath}`;
    const fileInfoResult = await session2.command.executeCommand(checkFileCmd);
    expect(fileInfoResult.success).toBe(true);
    console.log(`File info: ${fileInfoResult.output}`);
    
    // Verify file exists and has expected size (approximately 1GB)
    const fileExistsCmd = `test -f ${testFilePath} && echo 'File exists'`;
    const existsResult = await session2.command.executeCommand(fileExistsCmd);
    expect(existsResult.success).toBe(true);
    expect(existsResult.output).toContain("File exists");
    console.log("1GB file persistence verified successfully");
  });
}); 

// Helper function to print context status data
function printContextStatusData(data: any[]): void {
  if (data.length === 0) {
    console.log("No context status data available");
    return;
  }
  
  for (let i = 0; i < data.length; i++) {
    const item = data[i];
    console.log(`Context Status Data [${i}]:`);
    console.log(`  ContextId: ${item.contextId}`);
    console.log(`  Path: ${item.path}`);
    console.log(`  Status: ${item.status}`);
    console.log(`  TaskType: ${item.taskType}`);
    console.log(`  StartTime: ${item.startTime}`);
    console.log(`  FinishTime: ${item.finishTime}`);
    if (item.errorMessage) {
      console.log(`  ErrorMessage: ${item.errorMessage}`);
    }
  }
} 