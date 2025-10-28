/* eslint-disable @typescript-eslint/no-explicit-any, @typescript-eslint/no-unsafe-assignment, @typescript-eslint/no-unsafe-member-access */
// eslint-disable-next-line @typescript-eslint/no-var-requires
const { Browser, BrowserAgent } = require('../../dist/index.cjs');

class TestSchema {
  constructor() {
    this.title = "";
    this.content = "";
  }
}

describe('Browser Unit Tests', () => {
  let mockSession;
  let browser;

  beforeEach(() => {
    mockSession = {
      getAPIKey: jest.fn().mockReturnValue('test-api-key'),
      getSessionId: jest.fn().mockReturnValue('test-session-id'),
      getClient: jest.fn().mockReturnValue({
        initBrowser: jest.fn().mockResolvedValue({
          body: {
            data: {
              port: 9222,
              endpoint: 'ws://localhost:9222'
            }
          }
        })
      }),
      callMcpTool: jest.fn().mockResolvedValue({
        success: true,
        data: '{"success": true, "message": "test"}',
        errorMessage: '',
        requestId: 'test-request-id'
      }),
      getLink: jest.fn().mockResolvedValue({
        success: true,
        data: 'ws://localhost:9222',
        requestId: 'test-request-id'
      })
    };
    browser = new Browser(mockSession);
  });

  test('should create browser instance', () => {
    expect(browser).toBeDefined();
    expect(browser.agent).toBeInstanceOf(BrowserAgent);
  });

  test('should initialize browser', async () => {
    const option = { persistentPath: '/tmp/browser' };
    const result = await browser.initializeAsync(option);
    
    expect(result).toBe(true);
    expect(browser.isInitialized()).toBe(true);
    
    const savedOption = browser.getOption();
    expect(savedOption).toBeDefined();
    expect(savedOption.useStealth).toBe(false); // Default value
    expect(savedOption.userAgent).toBeUndefined();
    expect(savedOption.viewport).toBeUndefined();
    expect(savedOption.screen).toBeUndefined();
    expect(savedOption.fingerprint).toBeUndefined();
    expect(savedOption.proxies).toBeUndefined();
  });

  test('should get endpoint URL when initialized', async () => {
    const option = { persistentPath: '/tmp/browser' };
    await browser.initializeAsync(option);
    
    const endpointUrl = await browser.getEndpointUrl();
    expect(endpointUrl).toBe('ws://localhost:9222');
    expect(mockSession.getLink).toHaveBeenCalled();
  });

  test('should throw error when getting endpoint URL without initialization', async () => {
    await expect(browser.getEndpointUrl()).rejects.toThrow('Browser is not initialized');
  });

  test('should perform act operation', async () => {
    await browser.initializeAsync({});
    
    const mockPage = { url: () => 'http://example.com' };
    const options = { action: 'Click search button' };
    
    const result = await browser.agent.act(options, mockPage);
    
    expect(result.success).toBe(true);
    expect(mockSession.callMcpTool).toHaveBeenCalled();
    const [toolName, args] = mockSession.callMcpTool.mock.calls[0];
    expect(toolName).toBe('page_use_act');
    expect(typeof args).toBe('object');
  });

  test('should perform observe operation', async () => {
    await browser.initializeAsync({});
    
    mockSession.callMcpTool.mockResolvedValue({
      success: true,
      data: JSON.stringify([{
        selector: '#search-btn',
        description: 'Search button',
        method: 'click',
        arguments: '{}'
      }]),
      errorMessage: '',
      requestId: 'test-request-id'
    });
    
    const mockPage = { url: () => 'http://example.com' };
    const options = { instruction: 'Find the search button' };
    
    const [success, results] = await browser.agent.observe(options, mockPage);
    
    expect(success).toBe(true);
    expect(Array.isArray(results)).toBe(true);
    expect(results.length).toBe(1);
    expect(mockSession.callMcpTool).toHaveBeenCalled();
    const [toolName, args] = mockSession.callMcpTool.mock.calls[0];
    expect(toolName).toBe('page_use_observe');
    expect(typeof args).toBe('object');
  });

  test('should perform extract operation', async () => {
    await browser.initializeAsync({});
    
    mockSession.callMcpTool.mockResolvedValue({
      success: true,
      data: JSON.stringify({ title: 'Test Title' }),
      errorMessage: '',
      requestId: 'test-request-id'
    });
    
    const mockPage = { url: () => 'http://example.com' };
    const options = { 
      instruction: 'Extract the title', 
      schema: TestSchema 
    };
    
    const [success, result] = await browser.agent.extract(options, mockPage);
    
    expect(success).toBe(true);
    expect(result).toBeDefined();
    expect(result.title).toBe('Test Title');
    expect(mockSession.callMcpTool).toHaveBeenCalled();
    const [toolName, args] = mockSession.callMcpTool.mock.calls[0];
    expect(toolName).toBe('page_use_extract');
    expect(typeof args).toBe('object');
  });

  test('should handle act operation failure', async () => {
    await browser.initializeAsync({});
    
    mockSession.callMcpTool.mockResolvedValue({
      success: false,
      data: '',
      errorMessage: 'Test error',
      requestId: 'test-request-id'
    });
    
    const mockPage = { url: () => 'http://example.com' };
    const options = { action: 'Click search button' };
    
    const result = await browser.agent.act(options, mockPage);
    
    expect(result.success).toBe(false);
    expect(result.message).toBe('Test error');
  });

  test('should throw error when browser not initialized for operations', async () => {
    const mockPage = { url: () => 'http://example.com' };
    
    await expect(browser.agent.act({ action: 'test' }, mockPage)).rejects.toThrow('Browser must be initialized');
    await expect(browser.agent.observe({ instruction: 'test' }, mockPage)).rejects.toThrow('Browser must be initialized');
    await expect(browser.agent.extract({ instruction: 'test', schema: TestSchema }, mockPage)).rejects.toThrow('Browser must be initialized');
  });

  describe('Browser Options', () => {
    test('should handle browser options with all parameters', async () => {
      const option = {
        useStealth: true,
        userAgent: 'Test User Agent',
        viewport: { width: 1920, height: 1080 },
        screen: { width: 1920, height: 1080 },
        fingerprint: {
          devices: ['desktop'],
          operatingSystems: ['windows', 'macos'],
          locales: ['zh-CN']
        },
        proxies: [{
          type: 'wuying',
          strategy: 'polling',
          pollsize: 15
        }]
      };
      
      await browser.initializeAsync(option);
      const savedOption = browser.getOption();
      
      expect(savedOption).toBeDefined();
      expect(savedOption.useStealth).toBe(true);
      expect(savedOption.userAgent).toBe('Test User Agent');
      expect(savedOption.viewport.width).toBe(1920);
      expect(savedOption.viewport.height).toBe(1080);
      expect(savedOption.screen.width).toBe(1920);
      expect(savedOption.screen.height).toBe(1080);
      expect(savedOption.fingerprint.devices).toEqual(['desktop']);
      expect(savedOption.fingerprint.operatingSystems).toEqual(['windows', 'macos']);
      expect(savedOption.fingerprint.locales).toEqual(['zh-CN']);
      expect(savedOption.proxies).toBeDefined();
      expect(savedOption.proxies.length).toBe(1);
      expect(savedOption.proxies[0].type).toBe('wuying');
      expect(savedOption.proxies[0].strategy).toBe('polling');
      expect(savedOption.proxies[0].pollsize).toBe(15);
    });
  });
}); 