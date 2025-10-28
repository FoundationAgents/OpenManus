import { Extension, ExtensionOption, ExtensionsService } from "../../src/extension";
import { Context, ContextService } from "../../src/context";
import { AgentBayError } from "../../src/exceptions";
import * as sinon from "sinon";

describe("TestExtension", () => {
  describe("test_extension_initialization", () => {
    it("should initialize Extension with the correct attributes", () => {
      const extension = new Extension(
        "ext_123",
        "test-extension.zip",
        "2023-01-01T12:00:00Z"
      );

      expect(extension.id).toBe("ext_123");
      expect(extension.name).toBe("test-extension.zip");
      expect(extension.createdAt).toBe("2023-01-01T12:00:00Z");
    });

    it("should initialize Extension without createdAt", () => {
      const extension = new Extension("ext_456", "another-extension.zip");
      
      expect(extension.id).toBe("ext_456");
      expect(extension.name).toBe("another-extension.zip");
      expect(extension.createdAt).toBeUndefined();
    });
  });
});

describe("TestExtensionOption", () => {
  describe("test_extension_option_initialization", () => {
    it("should initialize ExtensionOption with valid parameters", () => {
      const option = new ExtensionOption("context_123", ["ext_1", "ext_2"]);
      
      expect(option.contextId).toBe("context_123");
      expect(option.extensionIds).toEqual(["ext_1", "ext_2"]);
      expect(option.validate()).toBe(true);
    });

    it("should throw error for empty contextId", () => {
      expect(() => {
        new ExtensionOption("", ["ext_1"]);
      }).toThrow("contextId cannot be empty");
    });

    it("should throw error for empty extensionIds", () => {
      expect(() => {
        new ExtensionOption("context_123", []);
      }).toThrow("extensionIds cannot be empty");
    });
  });

  describe("test_extension_option_string_representations", () => {
    it("should provide proper string representations", () => {
      const option = new ExtensionOption("context_123", ["ext_1", "ext_2"]);
      
      expect(option.toString()).toContain("context_123");
      expect(option.toString()).toContain('["ext_1","ext_2"]');
      expect(option.toDisplayString()).toBe("Extension Config: 2 extension(s) in context 'context_123'");
    });
  });

  describe("test_extension_option_validation", () => {
    it("should validate correctly for valid configuration", () => {
      const validOption = new ExtensionOption("context_123", ["ext_1", "ext_2"]);
      expect(validOption.validate()).toBe(true);
    });

    it("should validate correctly for invalid configuration", () => {
      // Test validation with empty extension ID
      const invalidOption = new ExtensionOption("context_123", ["ext_1", ""]);
      expect(invalidOption.validate()).toBe(false);
    });
  });
});

describe("TestExtensionsService", () => {
  let mockExtensionsService: ExtensionsService;
  let mockAgentBay: any;
  let mockContextService: any;
  let sandbox: sinon.SinonSandbox;

  beforeEach(() => {
    sandbox = sinon.createSandbox();

    mockContextService = {
      get: sandbox.stub(),
      delete: sandbox.stub(),
      getFileUploadUrl: sandbox.stub(),
      deleteFile: sandbox.stub(),
      listFiles: sandbox.stub(),
    };

    mockAgentBay = {
      context: mockContextService,
      getAPIKey: sandbox.stub().returns("test-api-key"),
    };

    // Setup default successful context initialization
    const mockContext = new Context("ctx_123", "test-extensions", "available");
    const contextResult = {
      requestId: "req_123",
      success: true,
      contextId: "ctx_123",
      context: mockContext,
    };
    mockContextService.get.resolves(contextResult);

    mockExtensionsService = new ExtensionsService(mockAgentBay, "test-extensions");
  });

  afterEach(() => {
    sandbox.restore();
  });

  describe("test_extensions_service_constructor", () => {
    it("should create service with provided context name", () => {
      expect(mockExtensionsService).toBeDefined();
    });

    it("should generate default context name when empty", () => {
      const service = new ExtensionsService(mockAgentBay);
      expect(service).toBeDefined();
    });

    it("should throw error for missing AgentBay", () => {
      expect(() => {
        new ExtensionsService(null as any);
      }).toThrow("AgentBay instance is required");
    });

    it("should throw error for AgentBay without context service", () => {
      const invalidAgentBay = { getAPIKey: () => "test-key" };
      expect(() => {
        new ExtensionsService(invalidAgentBay as any);
      }).toThrow("AgentBay instance must have a context service");
    });
  });

  describe("test_list_extensions_success", () => {
    it("should list extensions successfully", async () => {
      // Mock the response from the context service
      const mockFileListResult = {
        requestId: "req_123",
        success: true,
        entries: [
          {
            filePath: "/tmp/extensions/ext_123.zip",
            fileName: "ext_123.zip",
            gmtCreate: "2023-01-01T12:00:00Z",
          },
          {
            filePath: "/tmp/extensions/ext_456.zip",
            fileName: "ext_456.zip",
            gmtCreate: "2023-01-02T12:00:00Z",
          },
        ],
      };

      mockContextService.listFiles.resolves(mockFileListResult);

      // Call the method
      const extensions = await mockExtensionsService.list();

      // Verify the results
      expect(extensions).toHaveLength(2);
      expect(extensions[0].id).toBe("ext_123.zip");
      expect(extensions[0].name).toBe("ext_123.zip");
      expect(extensions[0].createdAt).toBe("2023-01-01T12:00:00Z");
      expect(extensions[1].id).toBe("ext_456.zip");
      expect(extensions[1].name).toBe("ext_456.zip");
      expect(extensions[1].createdAt).toBe("2023-01-02T12:00:00Z");

      expect(mockContextService.listFiles.calledOnce).toBe(true);
      expect(mockContextService.listFiles.calledWith("ctx_123", "/tmp/extensions", 1, 100)).toBe(true);
    });
  });

  describe("test_list_extensions_failure", () => {
    it("should handle list extensions failure", async () => {
      const mockFileListResult = {
        requestId: "req_123",
        success: false,
        entries: [],
      };

      mockContextService.listFiles.resolves(mockFileListResult);

      await expect(mockExtensionsService.list()).rejects.toThrow("Failed to list extensions");
    });

    it("should handle context service error", async () => {
      mockContextService.listFiles.rejects(new Error("Context API Error"));

      await expect(mockExtensionsService.list()).rejects.toThrow("An error occurred while listing browser extensions");
    });
  });

  describe("test_delete_extension_success", () => {
    it("should delete extension successfully", async () => {
      const mockDeleteResult = {
        requestId: "req_123",
        success: true,
        data: true,
      };

      mockContextService.deleteFile.resolves(mockDeleteResult);

      const result = await mockExtensionsService.delete("ext_123");

      expect(result).toBe(true);
      expect(mockContextService.deleteFile.calledOnce).toBe(true);
      expect(mockContextService.deleteFile.calledWith("ctx_123", "/tmp/extensions/ext_123")).toBe(true);
    });
  });

  describe("test_delete_extension_failure", () => {
    it("should handle delete extension failure", async () => {
      const mockDeleteResult = {
        requestId: "req_123",
        success: false,
        data: false,
      };

      mockContextService.deleteFile.resolves(mockDeleteResult);

      const result = await mockExtensionsService.delete("ext_123");

      expect(result).toBe(false);
    });
  });

  describe("test_create_extension_option_success", () => {
    it("should create ExtensionOption with current context", async () => {
      // First ensure service is initialized by calling a method
      const mockFileListResult = {
        requestId: "req_123",
        success: true,
        entries: [],
      };
      mockContextService.listFiles.resolves(mockFileListResult);
      await mockExtensionsService.list();
      
      const extensionIds = ["ext_1", "ext_2"];
      const option = mockExtensionsService.createExtensionOption(extensionIds);

      expect(option).toBeInstanceOf(ExtensionOption);
      expect(option.contextId).toBe("ctx_123");
      expect(option.extensionIds).toEqual(extensionIds);
    });
  });

  describe("test_create_extension_option_failure", () => {
    it("should throw error for empty extension IDs", () => {
      expect(() => {
        mockExtensionsService.createExtensionOption([]);
      }).toThrow("extensionIds cannot be empty");
    });

    it("should throw error when service not initialized", () => {
      const newService = new ExtensionsService(mockAgentBay, "test");
      expect(() => {
        newService.createExtensionOption(["ext_1"]);
      }).toThrow("Service not initialized");
    });
  });

  describe("test_cleanup_context_success", () => {
    it("should cleanup auto-created context successfully", async () => {
      const mockDeleteResult = {
        requestId: "req_123",
        success: true,
        data: true,
      };

      mockContextService.delete.resolves(mockDeleteResult);

      const result = await mockExtensionsService.cleanup();

      expect(result).toBe(true);
      expect(mockContextService.delete.calledOnce).toBe(true);
    });
  });

  describe("test_initialization_failure", () => {
    it("should handle initialization failure gracefully", async () => {
      // Create a service with failing context initialization
      const contextResult = {
        requestId: "req_123",
        success: false,
        contextId: "",
      };
      mockContextService.get.resolves(contextResult);

      const failingService = new ExtensionsService(mockAgentBay, "failing-context");

      // First method call should fail due to initialization error
      await expect(failingService.list()).rejects.toThrow("Failed to create extension repository context");
    });

    it("should handle context service error during initialization", async () => {
      mockContextService.get.rejects(new Error("Context initialization error"));

      const failingService = new ExtensionsService(mockAgentBay, "error-context");

      await expect(failingService.list()).rejects.toThrow("Failed to initialize ExtensionsService");
    });
  });
});