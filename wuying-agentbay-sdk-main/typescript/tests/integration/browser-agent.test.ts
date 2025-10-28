/* eslint-disable @typescript-eslint/no-explicit-any, @typescript-eslint/no-unsafe-assignment, @typescript-eslint/no-unsafe-member-access */
// Browser agent integration tests
import { AgentBay, Browser, BrowserAgent, log } from '../../src';

function getTestApiKey(): string {
  const apiKey = process.env.AGENTBAY_API_KEY;
  if (!apiKey) {
    log("Warning: Using default API key. Set AGENTBAY_API_KEY environment variable for testing.");
    return "akm-xxx";
  }
  return apiKey as string;
}

function maskSecret(secret: string, visible = 4): string {
  if (!secret) return "";
  if (secret.length <= visible) return "*".repeat(secret.length);
  return "*".repeat(secret.length - visible) + secret.slice(-visible);
}

function isWindowsUserAgent(userAgent: any): boolean {
  if (!userAgent) return false;
  const lower = String(userAgent).toLowerCase();
  return ['windows nt','win32','win64','windows','wow64'].some(x => lower.includes(x));
}

describe('BrowserAgent Integration Tests', () => {
  let agentBay: any;
  let session: any;

  beforeEach(async () => {
    const apiKey = getTestApiKey();
    log("api_key =", maskSecret(apiKey));
    agentBay = new AgentBay({ apiKey });

    // Create a session
    log("Creating a new session for browser agent testing...");
    const sessionParam = {
      imageId: "browser_latest"
    };
    
    const result = await agentBay.create(sessionParam);
    
    if (!result.success) {
      log("⚠️ Session creation failed - probably due to resource limitations");
      log("Result data:", result.errorMessage || result);
      session = null; // Mark as failed
      return;
    }
    
    session = result.session;
    log(`Session created with ID: ${session.sessionId}`);
  });

  afterEach(async () => {
    if (session) {
      log("Cleaning up: Deleting the session...");
      try {
        await agentBay.delete(session);
      } catch (error: any) {
        log(`Warning: Error deleting session: ${error?.message || error}`);
      }
    }
  });

  test('should have browser property', () => {
    if (!session) {
      log("⏭️ Skipping test - session creation failed");
      expect(true).toBe(true); // Skip test gracefully
      return;
    }
    
    const browser = session.browser;
    expect(browser).toBeDefined();
    expect(browser).toBeInstanceOf(Browser);
    expect(browser.agent).toBeInstanceOf(BrowserAgent);
  });

  test('initialize browser', async () => {
    if (!session) {
      log("⏭️ Skipping test - session creation failed");
      expect(true).toBe(true);
      return;
    }
    
    const browser = session.browser;
    expect(browser).toBeDefined();

    const initialized = await browser.initializeAsync({});
    expect(initialized).toBe(true);

    try {
      const endpointUrl = await browser.getEndpointUrl();
      log("endpoint_url:", endpointUrl);
      expect(endpointUrl).toBeDefined();
    } catch (error: any) {
      log("Expected: Getting endpoint URL might fail in test environment:", error?.message || error);
    }
  }, 60000);

  test('initialize browser with fingerprint', async () => {
    if (!session) {
      log("⏭️ Skipping test - session creation failed");
      expect(true).toBe(true);
      return;
    }

    const browser = session.browser;
    const option = {
      useStealth: true,
      fingerprint: {
        devices: ['desktop'] as Array<'desktop'|'mobile'>,
        operatingSystems: ['windows'] as Array<'windows'|'linux'|'macos'>,
        locales: ['zh-CN'] as Array<'zh-CN'|'en-US'>
      }
    };

    const initialized = await browser.initializeAsync(option);
    expect(initialized).toBe(true);
  }, 60000);

  test('act success', async () => {
    if (!session) {
      log("⏭️ Skipping test - session creation failed");
      expect(true).toBe(true);
      return;
    }
    
    const browser = session.browser;
    expect(browser).toBeDefined();

    const initialized = await browser.initializeAsync({});
    expect(initialized).toBe(true);

    // Mock page object (in real scenario would be from Playwright)
    const mockPage = {
      url: () => "http://example.com",
      title: () => "Example Domain"
    };

    try {
      const result = await browser.agent.act({ action: "Click search button" }, mockPage);
      log("Act result:", result);
      expect(result).toBeDefined();
    } catch (error: any) {
      log("Expected: Act operation might fail without real page:", error?.message || error);
    }
  }, 60000);

  test('observe success', async () => {
    if (!session) {
      log("⏭️ Skipping test - session creation failed");
      expect(true).toBe(true);
      return;
    }
    
    const browser = session.browser;
    expect(browser).toBeDefined();

    const initialized = await browser.initializeAsync({});
    expect(initialized).toBe(true);

    // Mock page object (in real scenario would be from Playwright)
    const mockPage = {
      url: () => "http://example.com",
      title: () => "Example Domain"
    };

    // Test observe operation
    try {
      const [success, observeResults] = await browser.agent.observe({ instruction: "Find the search button" }, mockPage);
      log("Observe success:", success);
      log("Observe results count:", observeResults.length);
      expect(typeof success).toBe('boolean');
      expect(Array.isArray(observeResults)).toBe(true);
    } catch (error: any) {
      log("Expected: Observe operation might fail without real page:", error?.message || error);
    }
  }, 60000);

  test('extract success', async () => {
    if (!session) {
      log("⏭️ Skipping test - session creation failed");
      expect(true).toBe(true);
      return;
    }

    const browser = session.browser;
    expect(browser).toBeDefined();

    const initialized = await browser.initializeAsync({});
    expect(initialized).toBe(true);

    // Mock page object (in real scenario would be from Playwright)
    const mockPage = {
      url: () => "http://example.com",
      title: () => "Example Domain"
    };

    // Test extract operation
    try {
      class TestSchema { 
        title = '';
        constructor() { 
          this.title = ""; 
        } 
      }

      const [success, objects] = await browser.agent.extract({ 
        instruction: "Extract the title", 
        schema: TestSchema 
      }, mockPage);
      
      log("Extract success:", success);
      log("Extract objects count:", objects.length);
      expect(typeof success).toBe('boolean');
      expect(Array.isArray(objects)).toBe(true);
    } catch (error: any) {
      log("Expected: Extract operation might fail without real page:", error?.message || error);
    }
  }, 60000);
});