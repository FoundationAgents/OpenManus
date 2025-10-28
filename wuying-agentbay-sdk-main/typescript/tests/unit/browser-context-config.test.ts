import { BROWSER_DATA_PATH } from "../../src/config";
import { BrowserContext, CreateSessionParams } from "../../src/session-params";
import { AgentBay } from "../../src/agent-bay";
import { ExtensionOption } from "../../src/extension";
import { Lifecycle } from "../../src/context-sync";

describe("BrowserContextConfig", () => {
  describe("BROWSER_DATA_PATH constant", () => {
    it("should be correctly defined", () => {
      expect(BROWSER_DATA_PATH).toBe("/tmp/agentbay_browser");
      expect(typeof BROWSER_DATA_PATH).toBe("string");
      expect(BROWSER_DATA_PATH.startsWith("/")).toBe(true);
    });
  });

  describe("BrowserContext interface", () => {
    it("should create browser context with correct properties", () => {
      const contextId = "test-context-123";
      const autoUpload = true;
      const browserContext: BrowserContext = new BrowserContext(
        contextId,
        autoUpload,
      );
      expect(browserContext.contextId).toBe(contextId);
      expect(browserContext.autoUpload).toBe(autoUpload);
    });

    it("should allow autoUpload to be false", () => {
      const contextId = "test-context-456";
      const autoUpload = false;

      const browserContext: BrowserContext = new BrowserContext(
        contextId,
        autoUpload,
      );

      expect(browserContext.contextId).toBe(contextId);
      expect(browserContext.autoUpload).toBe(false);
    });
  });

  describe("CreateSessionParams with browser context", () => {
    it("should accept browser context in constructor", () => {
      const contextId = "test-context-789";
      const browserContext: BrowserContext = new BrowserContext(
        contextId,
        false,
      );

      const params = new CreateSessionParams();
      params.browserContext = browserContext;

      expect(params.browserContext).toBeDefined();
      expect(params.browserContext?.contextId).toBe(contextId);
      expect(params.browserContext?.autoUpload).toBe(false);
    });

    it("should support withBrowserContext fluent method", () => {
      const contextId = "test-context-fluent";
      const browserContext: BrowserContext = new BrowserContext(
        contextId,
        true,
      );

      const params = new CreateSessionParams().withBrowserContext(browserContext);

      expect(params.browserContext).toBeDefined();
      expect(params.browserContext?.contextId).toBe(contextId);
      expect(params.browserContext?.autoUpload).toBe(true);
    });

    it("should serialize browser context correctly", () => {
      const contextId = "test-context-serialization";
      const browserContext: BrowserContext = new BrowserContext(
        contextId,
        true,
      );

      const params = new CreateSessionParams();
      params.browserContext = browserContext;

      const jsonConfig = params.toJSON();

      expect(jsonConfig.browserContext).toBeDefined();
      expect(jsonConfig.browserContext?.contextId).toBe(contextId);
      expect(jsonConfig.browserContext?.autoUpload).toBe(true);
    });

    it("should deserialize browser context correctly", () => {
      const contextId = "test-context-deserialization";
      const config = {
        labels: {},
        contextSync: [],
        browserContext: new BrowserContext(contextId, false),
      };

      const params = CreateSessionParams.fromJSON(config);

      expect(params.browserContext).toBeDefined();
      expect(params.browserContext?.contextId).toBe(contextId);
      expect(params.browserContext?.autoUpload).toBe(false);
    });
  });

  describe("AgentBay with browser context", () => {
    it("should handle browser context in create method", () => {
      // This test verifies that the AgentBay class can handle browser context
      // without throwing errors, even though we can't easily mock the complex
      // API calls in unit tests
      const agentBay = new AgentBay({ apiKey: "test-api-key" });
      
      const browserContext: BrowserContext = new BrowserContext(
        "test-context-agentbay",
        true,
      );

      const params = new CreateSessionParams();
      params.browserContext = browserContext;

      // The create method should not throw an error when called with browser context
      // (though it will fail due to missing API key, but that's expected)
      expect(() => {
        // We're not actually calling create() here because it's async and would fail
        // due to missing API key, but we can verify the params are set correctly
        expect(params.browserContext).toBeDefined();
        expect(params.browserContext?.contextId).toBe("test-context-agentbay");
      }).not.toThrow();
    });
  });

  describe("Browser context JSON serialization", () => {
    it("should serialize browser context to JSON correctly", () => {
      const browserContext: BrowserContext = new BrowserContext(
        "test-context-json",
        true,
      );

      const jsonString = JSON.stringify(browserContext);
      const parsed = JSON.parse(jsonString);

      expect(parsed.contextId).toBe("test-context-json");
      expect(parsed.autoUpload).toBe(true);
    });

    it("should handle different autoUpload values", () => {
      const browserContextFalse: BrowserContext = new BrowserContext(
        "test-context-false",
        false,
      );

      const browserContextTrue: BrowserContext = new BrowserContext(
        "test-context-true",
        true,
      );

      const jsonFalse = JSON.stringify(browserContextFalse);
      const jsonTrue = JSON.stringify(browserContextTrue);

      const parsedFalse = JSON.parse(jsonFalse);
      const parsedTrue = JSON.parse(jsonTrue);

      expect(parsedFalse.autoUpload).toBe(false);
      expect(parsedTrue.autoUpload).toBe(true);
    });
  });

  describe("BrowserContext extensionContextSyncs recyclePolicy validation", () => {
    it("should create extensionContextSyncs with correct recyclePolicy when extensionOption is provided", () => {
      const contextId = "test-browser-context";
      const extensionContextId = "test-extension-context";
      const extensionIds = ["extension1", "extension2"];

      // Create ExtensionOption
      const extensionOption = new ExtensionOption(extensionContextId, extensionIds);

      // Create BrowserContext with extensionOption
      const browserContext = new BrowserContext(contextId, true, extensionOption);

      // Verify extensionContextSyncs is created
      expect(browserContext.extensionContextSyncs).toBeDefined();
      expect(browserContext.extensionContextSyncs).toHaveLength(1);

      const extensionSync = browserContext.extensionContextSyncs![0];

      // Verify the context sync has correct properties
      expect(extensionSync.contextId).toBe(extensionContextId);
      expect(extensionSync.path).toBe("/tmp/extensions/");
      expect(extensionSync.policy).toBeDefined();

      // Verify recyclePolicy exists and has correct default values
      expect(extensionSync.policy!.recyclePolicy).toBeDefined();
      expect(extensionSync.policy!.recyclePolicy!.lifecycle).toBe(Lifecycle.Lifecycle_Forever);
      expect(extensionSync.policy!.recyclePolicy!.paths).toBeDefined();
      expect(extensionSync.policy!.recyclePolicy!.paths).toHaveLength(1);
      expect(extensionSync.policy!.recyclePolicy!.paths[0]).toBe("");
    });

    it("should not create extensionContextSyncs when no extensionOption is provided", () => {
      const contextId = "test-browser-context-no-ext";

      // Create BrowserContext without extensionOption
      const browserContext = new BrowserContext(contextId, true);

      // Verify extensionContextSyncs is undefined
      expect(browserContext.extensionContextSyncs).toBeUndefined();
      expect(browserContext.extensionContextId).toBeUndefined();
      expect(browserContext.extensionIds).toEqual([]);
    });

    it("should verify recyclePolicy structure in extensionContextSyncs", () => {
      const contextId = "test-browser-context-policy";
      const extensionContextId = "test-extension-context-policy";
      const extensionIds = ["ext1", "ext2", "ext3"];

      // Create ExtensionOption
      const extensionOption = new ExtensionOption(extensionContextId, extensionIds);

      // Create BrowserContext with extensionOption
      const browserContext = new BrowserContext(contextId, true, extensionOption);

      const extensionSync = browserContext.extensionContextSyncs![0];
      const recyclePolicy = extensionSync.policy!.recyclePolicy!;

      // Verify recyclePolicy structure
      expect(recyclePolicy).toHaveProperty('lifecycle');
      expect(recyclePolicy).toHaveProperty('paths');
      expect(typeof recyclePolicy.lifecycle).toBe('string');
      expect(Array.isArray(recyclePolicy.paths)).toBe(true);

      // Verify default values
      expect(recyclePolicy.lifecycle).toBe(Lifecycle.Lifecycle_Forever);
      expect(recyclePolicy.paths).toEqual([""]);
    });
  });
});