import { AgentBay, CreateSessionParams, Session } from "../../src";

function getTestAPIKey(): string {
  const apiKey = process.env.AGENTBAY_API_KEY;
  if (!apiKey) {
    console.warn(
      "Warning: AGENTBAY_API_KEY environment variable not set. Using default test key."
    );
    return "akm-xxx"; // Replace with your test API key
  }
  return apiKey;
}

function generateUniqueId(): string {
  const timestamp = Date.now() * 1000 + Math.floor(Math.random() * 1000);
  const randomPart = Math.floor(Math.random() * 10000);
  return `${timestamp}-${randomPart}`;
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

describe("AgentBay.list() Integration Tests", () => {
  let agentBay: AgentBay;
  let uniqueId: string;
  let testSessions: Session[] = [];

  beforeAll(async () => {
    const apiKey = getTestAPIKey();
    agentBay = new AgentBay({ apiKey });
    uniqueId = generateUniqueId();

    console.log(`Using unique ID for test: ${uniqueId}`);

    // Create multiple sessions with different labels for testing
    console.log("Creating session 1 with dev environment...");
    const params1: CreateSessionParams = {
      labels: {
        project: `list-test-${uniqueId}`,
        environment: "dev",
        owner: `test-${uniqueId}`,
      },
    };
    const result1 = await agentBay.create(params1);
    if (result1.success && result1.session) {
      testSessions.push(result1.session);
      console.log(`Session 1 created: ${result1.session.sessionId}`);
      console.log(`Request ID: ${result1.requestId}`);
    }

    console.log("Creating session 2 with staging environment...");
    const params2: CreateSessionParams = {
      labels: {
        project: `list-test-${uniqueId}`,
        environment: "staging",
        owner: `test-${uniqueId}`,
      },
    };
    const result2 = await agentBay.create(params2);
    if (result2.success && result2.session) {
      testSessions.push(result2.session);
      console.log(`Session 2 created: ${result2.session.sessionId}`);
      console.log(`Request ID: ${result2.requestId}`);
    }

    console.log("Creating session 3 with prod environment...");
    const params3: CreateSessionParams = {
      labels: {
        project: `list-test-${uniqueId}`,
        environment: "prod",
        owner: `test-${uniqueId}`,
      },
    };
    const result3 = await agentBay.create(params3);
    if (result3.success && result3.session) {
      testSessions.push(result3.session);
      console.log(`Session 3 created: ${result3.session.sessionId}`);
      console.log(`Request ID: ${result3.requestId}`);
    }

    // Verify all sessions were created
    if (testSessions.length !== 3) {
      throw new Error(`Failed to create all 3 test sessions. Only created ${testSessions.length} sessions.`);
    }

    // Wait longer for sessions to be fully created and labels to propagate
    console.log("Waiting 5 seconds for labels to propagate...");
    await sleep(5000);
  }, 60000);

  afterAll(async () => {
    console.log("Cleaning up: Deleting all test sessions...");
    for (const session of testSessions) {
      try {
        const result = await agentBay.delete(session);
        console.log(
          `Session ${session.sessionId} deleted. Success: ${result.success}, Request ID: ${result.requestId}`
        );
      } catch (error) {
        console.warn(
          `Warning: Error deleting session ${session.sessionId}: ${error}`
        );
      }
    }
  }, 60000);

  test("should list all sessions without any label filter", async () => {
    console.log("\n=== Testing list() without labels ===");

    const result = await agentBay.list();

    // Verify the result
    expect(result.success).toBe(true);
    expect(result.requestId).toBeDefined();
    expect(result.requestId).not.toBe("");
    expect(result.sessionIds).toBeDefined();

    console.log(`Total sessions found: ${result.totalCount}`);
    console.log(`Sessions in current page: ${result.sessionIds.length}`);
    console.log(`Request ID: ${result.requestId}`);
  });

  test("should list sessions with a single label filter", async () => {
    console.log("\n=== Testing list() with single label ===");

    const result = await agentBay.list({
      project: `list-test-${uniqueId}`,
    });

    // Verify the result
    expect(result.success).toBe(true);
    expect(result.requestId).toBeDefined();
    expect(result.requestId).not.toBe("");
    expect(result.sessionIds.length).toBeGreaterThanOrEqual(3);

    // Verify all returned sessions have the expected label
    const sessionIds = testSessions.map((s) => s.sessionId);
    const foundCount = result.sessionIds.filter((sid) =>
      sessionIds.includes(sid)
    ).length;

    expect(foundCount).toBe(3);

    console.log(`Found ${foundCount} test sessions`);
    console.log(`Total sessions with label: ${result.sessionIds.length}`);
    console.log(`Request ID: ${result.requestId}`);
  });

  test("should list sessions with multiple label filters", async () => {
    console.log("\n=== Testing list() with multiple labels ===");

    const result = await agentBay.list({
      project: `list-test-${uniqueId}`,
      environment: "dev",
    });

    // Verify the result
    expect(result.success).toBe(true);
    expect(result.requestId).toBeDefined();
    expect(result.requestId).not.toBe("");
    expect(result.sessionIds.length).toBeGreaterThanOrEqual(1);

    // Verify the dev session is in the results
    const devSessionId = testSessions[0].sessionId;
    const found = result.sessionIds.includes(devSessionId);

    expect(found).toBe(true);

    console.log(`Found dev session: ${found}`);
    console.log(`Total matching sessions: ${result.sessionIds.length}`);
    console.log(`Request ID: ${result.requestId}`);
  });

  test("should list sessions with pagination parameters", async () => {
    console.log("\n=== Testing list() with pagination ===");

    // List first page with limit of 2
    const resultPage1 = await agentBay.list(
      { project: `list-test-${uniqueId}` },
      1,
      2
    );

    // Verify first page
    expect(resultPage1.success).toBe(true);
    expect(resultPage1.requestId).toBeDefined();
    expect(resultPage1.requestId).not.toBe("");
    expect(resultPage1.data.length).toBeLessThanOrEqual(2);

    console.log(`Page 1 - Found ${resultPage1.data.length} sessions`);
    console.log(`Request ID: ${resultPage1.requestId}`);

    // If there are more results, test page 2
    if (resultPage1.nextToken) {
      const resultPage2 = await agentBay.list(
        { project: `list-test-${uniqueId}` },
        2,
        2
      );

      expect(resultPage2.success).toBe(true);
      expect(resultPage2.requestId).toBeDefined();
      expect(resultPage2.requestId).not.toBe("");

      console.log(`Page 2 - Found ${resultPage2.data.length} sessions`);
      console.log(`Request ID: ${resultPage2.requestId}`);
    }
  });

  test("should return empty results for non-matching labels", async () => {
    console.log("\n=== Testing list() with non-matching label ===");

    const result = await agentBay.list({
      project: `list-test-${uniqueId}`,
      environment: "nonexistent",
    });

    // Verify the result
    expect(result.success).toBe(true);
    expect(result.requestId).toBeDefined();
    expect(result.requestId).not.toBe("");

    // Verify our test sessions are NOT in the results
    const sessionIds = testSessions.map((s) => s.sessionId);
    const foundCount = result.sessionIds.filter((sid) =>
      sessionIds.includes(sid)
    ).length;

    expect(foundCount).toBe(0);

    console.log(`Correctly found ${foundCount} test sessions (expected 0)`);
    console.log(`Request ID: ${result.requestId}`);
  });

  test("should use default limit of 10 when not specified", async () => {
    console.log("\n=== Testing list() with default limit ===");

    const result = await agentBay.list({ owner: `test-${uniqueId}` });

    // Verify the result
    expect(result.success).toBe(true);
    expect(result.requestId).toBeDefined();
    expect(result.requestId).not.toBe("");
    expect(result.maxResults).toBe(10);

    console.log(`Max results: ${result.maxResults}`);
    console.log(`Request ID: ${result.requestId}`);
  });

  test("should include request_id in all responses", async () => {
    console.log("\n=== Testing list() request_id presence ===");

    // Test 1: No labels
    const result1 = await agentBay.list();
    expect(result1.requestId).toBeDefined();
    expect(result1.requestId).not.toBe("");
    console.log(`Test 1 Request ID: ${result1.requestId}`);

    // Test 2: With labels
    const result2 = await agentBay.list({
      project: `list-test-${uniqueId}`,
    });
    expect(result2.requestId).toBeDefined();
    expect(result2.requestId).not.toBe("");
    console.log(`Test 2 Request ID: ${result2.requestId}`);

    // Test 3: With pagination
    const result3 = await agentBay.list(
      { project: `list-test-${uniqueId}` },
      1,
      5
    );
    expect(result3.requestId).toBeDefined();
    expect(result3.requestId).not.toBe("");
    console.log(`Test 3 Request ID: ${result3.requestId}`);
  });

  test("should handle error scenarios correctly", async () => {
    console.log("\\n=== Testing list() error scenarios ===");

    // Test 1: Invalid page number (page = 0)
    console.log("\\nTest 1: page=0 should return error");
    const result1 = await agentBay.list(
      { project: `list-test-${uniqueId}` },
      0,
      5
    );
    expect(result1.success).toBe(false);
    expect(result1.errorMessage).toBeDefined();
    expect(result1.errorMessage).toContain("Page number must be >= 1");
    console.log(`✓ Correctly rejected page=0: ${result1.errorMessage}`);

    // Test 2: Invalid page number (page = -1)
    console.log("\\nTest 2: page=-1 should return error");
    const result2 = await agentBay.list(
      { project: `list-test-${uniqueId}` },
      -1,
      5
    );
    expect(result2.success).toBe(false);
    expect(result2.errorMessage).toBeDefined();
    expect(result2.errorMessage).toContain("Page number must be >= 1");
    console.log(`✓ Correctly rejected page=-1: ${result2.errorMessage}`);

    // Test 3: Out-of-range page number (page way beyond available data)
    console.log("\\nTest 3: page=999999 should return error (no more pages)");
    const result3 = await agentBay.list(
      { project: `list-test-${uniqueId}` },
      999999,
      2
    );
    expect(result3.success).toBe(false);
    expect(result3.errorMessage).toBeDefined();
    expect(result3.errorMessage).toContain("No more pages available");
    console.log(`✓ Correctly handled out-of-range page: ${result3.errorMessage}`);
  });

  test("should traverse all pages and verify pagination completeness", async () => {
    console.log("\\n=== Testing list() pagination completeness ===");

    const allSessionIds: string[] = [];
    let page = 1;
    const limit = 2;
    let totalCountFromApi = 0;

    console.log(`\\nTraversing all pages with limit=${limit}...`);

    while (true) {
      const result = await agentBay.list(
        { project: `list-test-${uniqueId}` },
        page,
        limit
      );

      // Verify each page request succeeds
      expect(result.success).toBe(true);
      expect(result.requestId).toBeDefined();

      // Collect session IDs
      allSessionIds.push(...result.sessionIds);
      totalCountFromApi = result.totalCount || 0;

      console.log(
        `Page ${page}: Found ${result.sessionIds.length} sessions, ` +
        `NextToken: ${result.nextToken ? "Yes" : "No"}, ` +
        `Total count: ${result.totalCount}`
      );

      // Verify page size constraint
      expect(result.sessionIds.length).toBeLessThanOrEqual(limit);

      // Check if we've reached the end
      if (!result.nextToken) {
        console.log(`\\n✓ Reached last page (page ${page})`);
        break;
      }

      page++;

      // Safety check to prevent infinite loop
      if (page > 100) {
        throw new Error("Pagination exceeded 100 pages, possible infinite loop");
      }
    }

    // Verify we collected at least our 3 test sessions
    expect(allSessionIds.length).toBeGreaterThanOrEqual(3);

    // Verify our test sessions are in the collected IDs
    const testSessionIds = testSessions.map((s) => s.sessionId);
    const foundCount = allSessionIds.filter((sid) =>
      testSessionIds.includes(sid)
    ).length;
    expect(foundCount).toBe(3);

    // Verify no duplicate session IDs
    const uniqueSessionIds = new Set(allSessionIds);
    expect(allSessionIds.length).toBe(uniqueSessionIds.size);

    console.log(`\\n✓ Pagination completeness verified:`);
    console.log(`  - Total pages traversed: ${page}`);
    console.log(`  - Total sessions collected: ${allSessionIds.length}`);
    console.log(`  - Total count from API: ${totalCountFromApi}`);
    console.log(`  - Found all 3 test sessions: Yes`);
    console.log(`  - No duplicates: Yes`);
  });

  test("should have consistent total_count across requests", async () => {
    console.log("\\n=== Testing list() total_count consistency ===");

    // Test 1: Verify total_count >= number of test sessions
    console.log("\\nTest 1: total_count should be >= 3 (our test sessions)");
    const result1 = await agentBay.list(
      { owner: `test-${uniqueId}` },
      undefined,
      10
    );

    expect(result1.success).toBe(true);
    expect(result1.totalCount).toBeGreaterThanOrEqual(3);
    console.log(`✓ total_count = ${result1.totalCount} (>= 3)`);

    // Test 2: Verify total_count remains consistent across multiple calls
    console.log("\\nTest 2: total_count should be consistent across multiple calls");
    const result2 = await agentBay.list(
      { owner: `test-${uniqueId}` },
      undefined,
      10
    );

    expect(result1.totalCount).toBe(result2.totalCount);
    console.log(`✓ total_count consistent: ${result1.totalCount} == ${result2.totalCount}`);

    // Test 3: Verify total_count matches actual sessions when collecting all pages
    console.log("\\nTest 3: total_count should match actual session count across all pages");

    const allSessionIds: string[] = [];
    let page = 1;
    const limit = 2;
    let expectedTotalCount = 0;

    while (true) {
      const result = await agentBay.list(
        { project: `list-test-${uniqueId}` },
        page,
        limit
      );

      if (!result.success) {
        break;
      }

      allSessionIds.push(...result.sessionIds);
      expectedTotalCount = result.totalCount || 0;

      if (!result.nextToken) {
        break;
      }

      page++;

      if (page > 100) {
        break;
      }
    }

    // The total_count should match the number of unique sessions collected
    const uniqueSessionIds = new Set(allSessionIds);
    expect(uniqueSessionIds.size).toBe(expectedTotalCount);

    console.log(
      `✓ total_count matches actual count: ` +
      `${expectedTotalCount} == ${uniqueSessionIds.size}`
    );

    // Test 4: Verify session_ids count <= total_count for each page
    console.log("\\nTest 4: session_ids count should be <= total_count on each page");
    const result = await agentBay.list(
      { owner: `test-${uniqueId}` },
      undefined,
      2
    );

    expect(result.sessionIds.length).toBeLessThanOrEqual(result.totalCount || 0);
    console.log(
      `✓ session_ids count (${result.sessionIds.length}) <= ` +
      `total_count (${result.totalCount})`
    );
  });
});

