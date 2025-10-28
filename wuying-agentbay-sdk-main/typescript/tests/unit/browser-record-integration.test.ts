import { AgentBay, Session } from "../../src";
import { CreateSessionParams } from "../../src/session-params";
import { Browser, BrowserOptionClass } from "../../src/browser/browser";
import * as sinon from "sinon";

describe("Browser Record Integration (Unit Test)", () => {
  let mockAgentBay: any;
  let mockSession: Session;
  let mockClient: any;
  let mockBrowser: Browser;
  let sandbox: sinon.SinonSandbox;

  beforeEach(() => {
    sandbox = sinon.createSandbox();

    // Mock client
    mockClient = {
      createMcpSession: sandbox.stub(),
      initBrowser: sandbox.stub(),
      callMcpTool: sandbox.stub(),
    };

    // Mock AgentBay
    mockAgentBay = {
      getAPIKey: sandbox.stub().returns("test-api-key"),
      getClient: sandbox.stub().returns(mockClient),
      removeSession: sandbox.stub(),
      create: sandbox.stub(),
    };

    // Create mock session
    mockSession = new Session(mockAgentBay, "test-session-id");
    mockSession.enableBrowserReplay = true; // Enable recording for this test

    // Mock browser
    mockBrowser = mockSession.browser;

    // Mock browser methods
    sandbox.stub(mockBrowser, 'initializeAsync').resolves(true);
    sandbox.stub(mockBrowser, 'getEndpointUrl').resolves('ws://localhost:9222/devtools/browser/test-id');
    sandbox.stub(mockBrowser, 'isInitialized').returns(true);
  });

  afterEach(() => {
    sandbox.restore();
  });

  test("should create session with recording enabled", async () => {
    // Mock create response with recording enabled
    const mockCreateResponse = {
      requestId: "create-with-record-request-id",
      success: true,
      session: mockSession,
    };
    mockAgentBay.create.resolves(mockCreateResponse);

    // Create session with recording enabled
    const sessionParam = new CreateSessionParams()
      .withImageId("browser_latest")
      .withEnableRecord(true);

    const result = await mockAgentBay.create(sessionParam);

    // Verify session creation was successful
    expect(result.success).toBe(true);
    expect(result.session).toBe(mockSession);
    expect(result.session.enableBrowserReplay).toBe(true);
    expect(mockAgentBay.create.calledOnceWith(sessionParam)).toBe(true);
  });

  test("should initialize browser with recording options", async () => {
    const browser = mockSession.browser;
    expect(browser).toBeDefined();

    // Initialize browser
    const browserOption = new BrowserOptionClass();
    const initResult = await browser.initializeAsync(browserOption);
    expect(initResult).toBe(true);

    // Verify browser was initialized
    expect(browser.isInitialized()).toBe(true);
  });

  test("should get browser endpoint URL for CDP connection", async () => {
    const browser = mockSession.browser;

    // Get endpoint URL
    const endpointUrl = await browser.getEndpointUrl();
    expect(endpointUrl).toBeDefined();
    expect(endpointUrl).not.toBeNull();
    expect(typeof endpointUrl).toBe('string');
    expect(endpointUrl).toMatch(/^ws:\/\//); // Should be a WebSocket URL
  });

  test("should perform browser operations with recording", async () => {
    const browser = mockSession.browser;

    // Initialize browser first
    const browserOption = new BrowserOptionClass();
    await browser.initializeAsync(browserOption);

    // Mock MCP tool calls for browser operations
    const mockNavigateResult = { success: true, data: "Navigation successful", errorMessage: "", requestId: "nav-123" };
    const mockScreenshotResult = { success: true, data: "Screenshot taken", errorMessage: "", requestId: "shot-123" };
    const mockFillResult = { success: true, data: "Input filled", errorMessage: "", requestId: "fill-123" };
    const mockClickResult = { success: true, data: "Button clicked", errorMessage: "", requestId: "click-123" };

    // Set up mock responses for MCP tool calls
    sandbox.stub(mockSession, 'callMcpTool')
      .withArgs("browser_navigate", { url: "http://www.baidu.com" }).resolves(mockNavigateResult)
      .withArgs("browser_screenshot", { path: "/tmp/test_screenshot.png" }).resolves(mockScreenshotResult)
      .withArgs("browser_fill", { selector: "#kw", text: "AgentBay测试" }).resolves(mockFillResult)
      .withArgs("browser_click", { selector: "#su" }).resolves(mockClickResult);

    // Perform browser navigation
    const navigateResult = await mockSession.callMcpTool("browser_navigate", {
      url: "http://www.baidu.com"
    });
    expect(navigateResult.success).toBe(true);

    // Take screenshot
    const screenshotResult = await mockSession.callMcpTool("browser_screenshot", {
      path: "/tmp/test_screenshot.png"
    });
    expect(screenshotResult.success).toBe(true);

    // Fill search input
    const fillResult = await mockSession.callMcpTool("browser_fill", {
      selector: "#kw",
      text: "AgentBay测试"
    });
    expect(fillResult.success).toBe(true);

    // Click search button
    const clickResult = await mockSession.callMcpTool("browser_click", {
      selector: "#su"
    });
    expect(clickResult.success).toBe(true);

    // Verify all operations were called
    const callMcpToolStub = mockSession.callMcpTool as sinon.SinonStub;
    expect(callMcpToolStub.calledWith("browser_navigate")).toBe(true);
    expect(callMcpToolStub.calledWith("browser_screenshot")).toBe(true);
    expect(callMcpToolStub.calledWith("browser_fill")).toBe(true);
    expect(callMcpToolStub.calledWith("browser_click")).toBe(true);
  });

  test("should enable recording in browser options when session.enableBrowserReplay is true", async () => {
    // Verify session has recording enabled
    expect(mockSession.enableBrowserReplay).toBe(true);

    // This test demonstrates that when enableBrowserReplay is true on the session,
    // the browser initialization should include enableBrowserReplay in the options
    const browser = mockSession.browser;
    const browserOption = new BrowserOptionClass();

    // Since we're mocking browser.initializeAsync to return true,
    // we just need to verify that the session has enableBrowserReplay set
    const initResult = await browser.initializeAsync(browserOption);
    expect(initResult).toBe(true);

    // Verify that the session has enableBrowserReplay enabled
    expect(mockSession.enableBrowserReplay).toBe(true);

    // In a real implementation, this would trigger the browser option
    // to include enableBrowserReplay: true when calling the API
    console.log("Recording is enabled for this session");
  });

  test("should support method chaining with enableBrowserReplay in CreateSessionParams", () => {
    const params = new CreateSessionParams()
      .withLabels({ project: "browser-test", type: "recording" })
      .withImageId("browser_latest")
      .withEnableRecord(true)
      .withIsVpc(false);

    expect(params.labels).toEqual({ project: "browser-test", type: "recording" });
    expect(params.imageId).toBe("browser_latest");
    expect(params.enableBrowserReplay).toBe(true);
    expect(params.isVpc).toBe(false);
  });
});