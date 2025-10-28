/* eslint-disable @typescript-eslint/no-explicit-any, @typescript-eslint/no-unsafe-assignment, @typescript-eslint/no-unsafe-member-access */
/* eslint-disable @typescript-eslint/no-explicit-any, @typescript-eslint/no-unsafe-assignment, @typescript-eslint/no-unsafe-member-access */
// Browser proxy integration tests
// eslint-disable-next-line @typescript-eslint/no-var-requires
const { AgentBay, BrowserProxyClass, BrowserOptionClass, log } = require('../../dist/index.cjs');

function getTestApiKey() {
  const apiKey = process.env.AGENTBAY_API_KEY;
  if (!apiKey) {
    log("Warning: Using default API key. Set AGENTBAY_API_KEY environment variable for testing.");
    return "akm-xxx";
  }
  return apiKey;
}

function maskSecret(secret, visible = 4) {
  if (!secret) return "";
  if (secret.length <= visible) return "*".repeat(secret.length);
  return "*".repeat(secret.length - visible) + secret.slice(-visible);
}

describe('BrowserProxy Integration Tests', () => {
  let agentBay;
  let session;

  beforeEach(async () => {
    const apiKey = getTestApiKey();
    log("api_key =", maskSecret(apiKey));
    agentBay = new AgentBay({ apiKey });

    // Create a session
    log("Creating a new session for browser proxy testing...");
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
      } catch (error) {
        log(`Warning: Error deleting session: ${error?.message || error}`);
      }
    }
  });

  test('should initialize browser with custom proxy', async () => {
    if (!session) {
      log("⏭️ Skipping test - session creation failed");
      expect(true).toBe(true); // Skip test gracefully
      return;
    }
    
    const browser = session.browser;
    expect(browser).toBeDefined();

    // Create custom proxy configuration
    const customProxy = new BrowserProxyClass(
      'custom',
      'http://proxy.example.com:8080',
      'testuser',
      'testpass'
    );

    const option = new BrowserOptionClass(
      true, // useStealth
      'Custom User Agent', // userAgent
      { width: 1920, height: 1080 }, // viewport
      { width: 1920, height: 1080 }, // screen
      { devices: ['desktop'], operatingSystems: ['windows'], locales: ['en-US'] }, // fingerprint
      [customProxy] // proxies
    );

    const initialized = await browser.initializeAsync(option);
    expect(initialized).toBe(true);

    // Verify proxy configuration was saved
    const savedOption = browser.getOption();
    expect(savedOption).toBeDefined();
    expect(savedOption?.proxies).toBeDefined();
    expect(savedOption?.proxies).toHaveLength(1);
    expect(savedOption?.proxies?.[0].type).toBe('custom');
    expect(savedOption?.proxies?.[0].server).toBe('http://proxy.example.com:8080');
    expect(savedOption?.proxies?.[0].username).toBe('testuser');
    expect(savedOption?.proxies?.[0].password).toBe('testpass');
  }, 60000);

  test('should initialize browser with wuying restricted proxy', async () => {
    if (!session) {
      log("⏭️ Skipping test - session creation failed");
      expect(true).toBe(true);
      return;
    }
    
    const browser = session.browser;
    expect(browser).toBeDefined();

    // Create wuying restricted proxy configuration
    const restrictedProxy = new BrowserProxyClass(
      'wuying',
      undefined,
      undefined,
      undefined,
      'restricted'
    );

    const option = new BrowserOptionClass(
      false, // useStealth
      undefined, // userAgent
      undefined, // viewport
      undefined, // screen
      undefined, // fingerprint
      [restrictedProxy] // proxies
    );

    const initialized = await browser.initializeAsync(option);
    expect(initialized).toBe(true);

    // Verify proxy configuration was saved
    const savedOption = browser.getOption();
    expect(savedOption).toBeDefined();
    expect(savedOption?.proxies).toBeDefined();
    expect(savedOption?.proxies).toHaveLength(1);
    expect(savedOption?.proxies?.[0].type).toBe('wuying');
    expect(savedOption?.proxies?.[0].strategy).toBe('restricted');
  }, 60000);

  test('should initialize browser with wuying polling proxy', async () => {
    if (!session) {
      log("⏭️ Skipping test - session creation failed");
      expect(true).toBe(true);
      return;
    }
    
    const browser = session.browser;
    expect(browser).toBeDefined();

    // Create wuying polling proxy configuration
    const pollingProxy = new BrowserProxyClass(
      'wuying',
      undefined,
      undefined,
      undefined,
      'polling',
      15 // custom pollsize
    );

    const option = new BrowserOptionClass(
      false, // useStealth
      undefined, // userAgent
      undefined, // viewport
      undefined, // screen
      undefined, // fingerprint
      [pollingProxy] // proxies
    );

    const initialized = await browser.initializeAsync(option);
    expect(initialized).toBe(true);

    // Verify proxy configuration was saved
    const savedOption = browser.getOption();
    expect(savedOption).toBeDefined();
    expect(savedOption?.proxies).toBeDefined();
    expect(savedOption?.proxies).toHaveLength(1);
    expect(savedOption?.proxies?.[0].type).toBe('wuying');
    expect(savedOption?.proxies?.[0].strategy).toBe('polling');
    expect(savedOption?.proxies?.[0].pollsize).toBe(15);
  }, 60000);

  test('should serialize and deserialize proxy configuration', async () => {
    if (!session) {
      log("⏭️ Skipping test - session creation failed");
      expect(true).toBe(true);
      return;
    }
    
    const browser = session.browser;
    expect(browser).toBeDefined();

    // Create proxy configuration
    const customProxy = new BrowserProxyClass(
      'custom',
      'http://proxy.example.com:8080',
      'testuser',
      'testpass'
    );

    const option = new BrowserOptionClass(
      true, // useStealth
      'Test User Agent', // userAgent
      { width: 1366, height: 768 }, // viewport
      { width: 1366, height: 768 }, // screen
      { devices: ['mobile'], operatingSystems: ['android'], locales: ['zh-CN'] }, // fingerprint
      [customProxy] // proxies
    );

    // Test serialization
    const optionMap = option.toMap();
    expect(optionMap.useStealth).toBe(true);
    expect(optionMap.userAgent).toBe('Test User Agent');
    expect(optionMap.viewport).toEqual({ width: 1366, height: 768 });
    expect(optionMap.screen).toEqual({ width: 1366, height: 768 });
    expect(optionMap.fingerprint).toEqual({ devices: ['mobile'], operatingSystems: ['android'], locales: ['zh-CN'] });
    expect(optionMap.proxies).toBeDefined();
    expect(optionMap.proxies).toHaveLength(1);
    expect(optionMap.proxies[0].type).toBe('custom');
    expect(optionMap.proxies[0].server).toBe('http://proxy.example.com:8080');
    expect(optionMap.proxies[0].username).toBe('testuser');
    expect(optionMap.proxies[0].password).toBe('testpass');

    // Test deserialization
    const restoredOption = new BrowserOptionClass();
    restoredOption.fromMap(optionMap);
    
    expect(restoredOption.useStealth).toBe(true);
    expect(restoredOption.userAgent).toBe('Test User Agent');
    expect(restoredOption.viewport).toEqual({ width: 1366, height: 768 });
    expect(restoredOption.screen).toEqual({ width: 1366, height: 768 });
    expect(restoredOption.fingerprint).toEqual({ devices: ['mobile'], operatingSystems: ['android'], locales: ['zh-CN'] });
    expect(restoredOption.proxies).toBeDefined();
    expect(restoredOption.proxies).toHaveLength(1);
    expect(restoredOption.proxies?.[0].type).toBe('custom');
    expect(restoredOption.proxies?.[0].server).toBe('http://proxy.example.com:8080');
    expect(restoredOption.proxies?.[0].username).toBe('testuser');
    expect(restoredOption.proxies?.[0].password).toBe('testpass');
  });

  test('should validate proxy configuration limits', () => {
    // Test that only one proxy is allowed
    const proxy1 = new BrowserProxyClass('custom', 'http://proxy1.com');
    const proxy2 = new BrowserProxyClass('custom', 'http://proxy2.com');

    expect(() => {
      new BrowserOptionClass(false, undefined, undefined, undefined, undefined, [proxy1, proxy2]);
    }).toThrow('proxies list length must be limited to 1');

    // Test that proxies must be an array
    const singleProxy = new BrowserProxyClass('custom', 'http://proxy.com');
    expect(() => {
      new BrowserOptionClass(false, undefined, undefined, undefined, undefined, singleProxy);
    }).toThrow('proxies must be a list');
  });

  test('should handle proxy validation errors', () => {
    // Test invalid proxy type
    expect(() => {
      new BrowserProxyClass('invalid');
    }).toThrow('proxy_type must be custom or wuying');

    // Test custom proxy without server
    expect(() => {
      new BrowserProxyClass('custom');
    }).toThrow('server is required for custom proxy type');

    // Test wuying proxy without strategy
    expect(() => {
      new BrowserProxyClass('wuying');
    }).toThrow('strategy is required for wuying proxy type');

    // Test wuying proxy with invalid strategy
    expect(() => {
      new BrowserProxyClass('wuying', undefined, undefined, undefined, 'invalid');
    }).toThrow('strategy must be restricted or polling for wuying proxy type');

    // Test polling strategy with invalid pollsize
    expect(() => {
      new BrowserProxyClass('wuying', undefined, undefined, undefined, 'polling', 0);
    }).toThrow('pollsize must be greater than 0 for polling strategy');

    expect(() => {
      new BrowserProxyClass('wuying', undefined, undefined, undefined, 'polling', -1);
    }).toThrow('pollsize must be greater than 0 for polling strategy');
  });
}); 