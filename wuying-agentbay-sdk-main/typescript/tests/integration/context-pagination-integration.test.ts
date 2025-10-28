import { AgentBay } from "../../src/agent-bay";
import { ContextListParams } from "../../src/context";

describe("ContextPaginationIntegration", () => {
  let agentBay: AgentBay;
  const contextNames: string[] = [];
  
  // Skip tests if no API key is available or in CI environment
  const apiKey = process.env.AGENTBAY_API_KEY;
  const shouldSkip = !apiKey || process.env.CI;
  
  beforeAll(async () => {
    if (shouldSkip) {
      return;
    }
    
    // Initialize AgentBay client
    agentBay = new AgentBay({ apiKey: apiKey! });
    
    // Create multiple contexts for testing pagination
    for (let i = 0; i < 15; i++) {
      const contextName = `test-pagination-ts-${Date.now()}-${i}`;
      const contextResult = await agentBay.context.create(contextName);
      if (contextResult.success && contextResult.context) {
        contextNames.push(contextName);
        console.log(`Created context: ${contextName} (ID: ${contextResult.context.id})`);
      } else {
        throw new Error(`Failed to create context ${contextName}`);
      }
    }
    
    // Wait a moment for all contexts to be fully created
    await new Promise(resolve => setTimeout(resolve, 2000));
  });
  
  afterAll(async () => {
    if (shouldSkip) {
      return;
    }
    
    // Clean up created contexts
    for (const contextName of contextNames) {
      try {
        const contextResult = await agentBay.context.get(contextName, false);
        if (contextResult.success && contextResult.context) {
          await agentBay.context.delete(contextResult.context);
          console.log(`Deleted context: ${contextName} (ID: ${contextResult.context.id})`);
        }
      } catch (e) {
        console.warn(`Warning: Failed to delete context ${contextName}: ${e}`);
      }
    }
  });
  
  it("should list contexts with default pagination (first page)", async () => {
    if (shouldSkip) {
      console.log("Skipping test: No API key available or running in CI");
      return;
    }
    
    console.log("Test 1: Listing contexts with default pagination (first page)");
    const params: ContextListParams = {
      maxResults: 10
    };
    
    const listResult = await agentBay.context.list(params);
    
    expect(listResult.success).toBe(true);
    expect(listResult.contexts.length).toBe(10);
    
    console.log(`First page: Got ${listResult.contexts.length} contexts (RequestID: ${listResult.requestId})`);
    console.log(`NextToken: ${listResult.nextToken}, MaxResults: ${listResult.maxResults}, TotalCount: ${listResult.totalCount}`);
  });
  
  it("should list contexts with custom page size", async () => {
    if (shouldSkip) {
      console.log("Skipping test: No API key available or running in CI");
      return;
    }
    
    console.log("Test 2: Listing contexts with custom page size (5 per page)");
    const params: ContextListParams = {
      maxResults: 5
    };
    
    const listResult = await agentBay.context.list(params);
    
    expect(listResult.success).toBe(true);
    expect(listResult.contexts.length).toBe(5);
    
    console.log(`Custom page size: Got ${listResult.contexts.length} contexts (RequestID: ${listResult.requestId})`);
    console.log(`NextToken: ${listResult.nextToken}, MaxResults: ${listResult.maxResults}, TotalCount: ${listResult.totalCount}`);
  });
  
  it("should get second page using NextToken", async () => {
    if (shouldSkip) {
      console.log("Skipping test: No API key available or running in CI");
      return;
    }
    
    console.log("Test 3: Getting second page using NextToken");
    
    // First, get the first page to obtain the NextToken
    const params1: ContextListParams = {
      maxResults: 5
    };
    const firstPageResult = await agentBay.context.list(params1);
    
    if (firstPageResult.nextToken) {
      // Get second page using NextToken
      const params2: ContextListParams = {
        maxResults: 5,
        nextToken: firstPageResult.nextToken
      };
      
      const secondPageResult = await agentBay.context.list(params2);
      
      expect(secondPageResult.success).toBe(true);
      
      console.log(`Second page: Got ${secondPageResult.contexts.length} contexts (RequestID: ${secondPageResult.requestId})`);
      console.log(`NextToken: ${secondPageResult.nextToken}, MaxResults: ${secondPageResult.maxResults}, TotalCount: ${secondPageResult.totalCount}`);
    } else {
      console.log("No NextToken available for second page test");
    }
  });
  
  it("should list contexts with larger page size", async () => {
    if (shouldSkip) {
      console.log("Skipping test: No API key available or running in CI");
      return;
    }
    
    console.log("Test 4: Listing contexts with larger page size (20 per page)");
    const params: ContextListParams = {
      maxResults: 20
    };
    
    const listResult = await agentBay.context.list(params);
    
    expect(listResult.success).toBe(true);
    // Should get all contexts (up to 15) since we only created 15
    expect(listResult.contexts.length).toBeGreaterThanOrEqual(10);
    
    console.log(`Larger page size: Got ${listResult.contexts.length} contexts (RequestID: ${listResult.requestId})`);
    console.log(`NextToken: ${listResult.nextToken}, MaxResults: ${listResult.maxResults}, TotalCount: ${listResult.totalCount}`);
  });
  
  it("should list contexts with nil parameters (should use defaults)", async () => {
    if (shouldSkip) {
      console.log("Skipping test: No API key available or running in CI");
      return;
    }
    
    console.log("Test 5: Listing contexts with nil parameters (should use defaults)");
    const listResult = await agentBay.context.list(undefined);
    
    expect(listResult.success).toBe(true);
    // Note: We're not checking for a specific number of contexts since the API behavior
    // may vary, but we're ensuring the call succeeds and returns some data
    expect(listResult.contexts).toBeDefined();
    
    console.log(`Nil parameters: Got ${listResult.contexts.length} contexts (RequestID: ${listResult.requestId})`);
    if (listResult.nextToken) {
      console.log(`NextToken: ${listResult.nextToken}, MaxResults: ${listResult.maxResults}, TotalCount: ${listResult.totalCount}`);
    }
  });
});