import { Context, ContextService } from "../../src/context";
import { APIError } from "../../src/exceptions";
import * as sinon from "sinon";

describe("TestContext", () => {
  describe("test_context_initialization", () => {
    it("should initialize Context with the correct attributes", () => {
      const context = new Context(
        "test-id",
        "test-context",
        "available",
        "2025-05-29T12:00:00Z",
        "2025-05-29T12:30:00Z",
        "linux"
      );

      expect(context.id).toBe("test-id");
      expect(context.name).toBe("test-context");
      expect(context.state).toBe("available");
      expect(context.createdAt).toBe("2025-05-29T12:00:00Z");
      expect(context.lastUsedAt).toBe("2025-05-29T12:30:00Z");
      expect(context.osType).toBe("linux");
    });
  });
});

describe("TestContextService", () => {
  let mockContextService: ContextService;
  let mockAgentBay: any;
  let mockClient: any;
  let sandbox: sinon.SinonSandbox;

  beforeEach(() => {
    sandbox = sinon.createSandbox();

    mockClient = {
      listContexts: sandbox.stub(),
      getContext: sandbox.stub(),
      modifyContext: sandbox.stub(),
      deleteContext: sandbox.stub(),
    };

    mockAgentBay = {
      getAPIKey: sandbox.stub().returns("test-api-key"),
      getClient: sandbox.stub().returns(mockClient),
    };

    mockContextService = new ContextService(mockAgentBay);
  });

  afterEach(() => {
    sandbox.restore();
  });

  describe("test_list_contexts_success", () => {
    it("should list contexts successfully", async () => {
      // Mock the response from the API
      const mockResponse = {
        body: {
          data: [
            {
              id: "context-1",
              name: "context-1-name",
              state: "available",
              createTime: "2025-05-29T12:00:00Z",
              lastUsedTime: "2025-05-29T12:30:00Z",
              osType: "linux",
            },
            {
              id: "context-2",
              name: "context-2-name",
              state: "in-use",
              createTime: "2025-05-29T13:00:00Z",
              lastUsedTime: "2025-05-29T13:30:00Z",
              osType: "windows",
            },
          ],
          requestId: "test-list-request-id",
        },
        statusCode: 200,
      };

      mockClient.listContexts.resolves(mockResponse);

      // Call the method
      const result = await mockContextService.list();

      // Verify ContextListResult structure
      expect(result.success).toBe(true);
      expect(result.requestId).toBe("test-list-request-id");
      expect(result.contexts).toHaveLength(2);
      expect(result.errorMessage).toBeUndefined();

      expect(result.contexts[0].id).toBe("context-1");
      expect(result.contexts[0].name).toBe("context-1-name");
      expect(result.contexts[0].state).toBe("available");
      expect(result.contexts[1].id).toBe("context-2");
      expect(result.contexts[1].name).toBe("context-2-name");
      expect(result.contexts[1].state).toBe("in-use");

      expect(mockClient.listContexts.calledOnce).toBe(true);
    });
  });

  describe("test_list_contexts_failure", () => {
    it("should handle list contexts failure", async () => {
      mockClient.listContexts.rejects(new Error("API Error"));

      const result = await mockContextService.list();

      // Verify error result structure
      expect(result.success).toBe(false);
      expect(result.requestId).toBe("");
      expect(result.contexts).toEqual([]);
    });
  });

  describe("test_get_context_success", () => {
    it("should get a context successfully", async () => {
      // Mock the get context response
      const mockGetResponse = {
        body: {
          data: { id: "context-1" },
          requestId: "test-get-request-id",
        },
        statusCode: 200,
      };
      mockClient.getContext.resolves(mockGetResponse);

      // Mock the list response to get full context details
      const mockListResponse = {
        body: {
          data: [
            {
              id: "context-1",
              name: "test-context",
              state: "available",
              createTime: "2025-05-29T12:00:00Z",
              lastUsedTime: "2025-05-29T12:30:00Z",
              osType: "linux",
            },
          ],
          requestId: "test-list-request-id",
        },
        statusCode: 200,
      };
      mockClient.listContexts.resolves(mockListResponse);

      // Call the method
      const result = await mockContextService.get("test-context");

      // Verify ContextResult structure
      expect(result.success).toBe(true);
      expect(result.requestId).toBe("test-get-request-id");
      expect(result.contextId).toBe("context-1");
      expect(result.context).not.toBeUndefined();
      expect(result.errorMessage).toBeUndefined();

      expect(result.context!.id).toBe("context-1");
      expect(result.context!.name).toBe("test-context");
      expect(result.context!.state).toBe("available");

      expect(mockClient.getContext.calledOnce).toBe(true);
      expect(mockClient.listContexts.calledOnce).toBe(true);
    });
  });

  describe("test_get_context_failure", () => {
    it("should handle get context failure", async () => {
      mockClient.getContext.rejects(new Error("API Error"));

      const result = await mockContextService.get("test-context");

      // Verify error result structure
      expect(result.success).toBe(false);
      expect(result.requestId).toBe("");
      expect(result.contextId).toBe("");
      expect(result.context).toBeUndefined();
    });
  });

  describe("test_create_context_success", () => {
    it("should create a context successfully", async () => {
      // Mock the get context response (create via get with allowCreate=true)
      const mockGetResponse = {
        body: {
          data: { id: "new-context-id" },
          requestId: "test-create-request-id",
        },
        statusCode: 200,
      };
      mockClient.getContext.resolves(mockGetResponse);

      // Mock the list response to get full context details
      const mockListResponse = {
        body: {
          data: [
            {
              id: "new-context-id",
              name: "new-context",
              state: "available",
              createTime: "2025-05-29T12:00:00Z",
              lastUsedTime: "2025-05-29T12:30:00Z",
              osType: null,
            },
          ],
          requestId: "test-list-request-id",
        },
        statusCode: 200,
      };
      mockClient.listContexts.resolves(mockListResponse);

      // Call the method
      const result = await mockContextService.create("new-context");

      // Verify ContextResult structure
      expect(result.success).toBe(true);
      expect(result.requestId).toBe("test-create-request-id");
      expect(result.contextId).toBe("new-context-id");
      expect(result.context).not.toBeUndefined();
      expect(result.errorMessage).toBeUndefined();

      expect(result.context!.id).toBe("new-context-id");
      expect(result.context!.name).toBe("new-context");
      expect(result.context!.state).toBe("available");

      expect(mockClient.getContext.calledOnce).toBe(true);
      expect(mockClient.listContexts.calledOnce).toBe(true);
    });
  });

  describe("test_update_context_success", () => {
    it("should update a context successfully", async () => {
      // Create a context to update
      const context = new Context(
        "context-to-update",
        "updated-name",
        "available"
      );

      // Mock the API response
      const mockResponse = {
        body: {
          code: "ok",
          httpStatusCode: 200,
          success: true,
          requestId: "test-update-request-id",
        },
        statusCode: 200,
      };
      mockClient.modifyContext.resolves(mockResponse);

      // Call the method
      const result = await mockContextService.update(context);

      // Verify OperationResult structure
      expect(result.success).toBe(true);
      expect(result.requestId).toBe("test-update-request-id");
      expect(result.data).toBe(true);
      expect(result.errorMessage).toBe("");

      expect(mockClient.modifyContext.calledOnce).toBe(true);
    });
  });

  describe("test_update_context_failure", () => {
    it("should handle update context failure", async () => {
      const context = new Context("context-id", "context-name", "available");

      mockClient.modifyContext.rejects(new Error("API Error"));

      const result = await mockContextService.update(context);

      // Verify error result structure
      expect(result.success).toBe(false);
      expect(result.requestId).toBe("");
      expect(result.errorMessage).toContain("Failed to update context");
    });
  });

  describe("test_delete_context_success", () => {
    it("should delete a context successfully", async () => {
      // Create a context to delete
      const context = new Context(
        "context-to-delete",
        "context-name",
        "available"
      );

      // Mock the API response with requestId in body
      const mockResponse = {
        body: {
          code: "ok",
          httpStatusCode: 200,
          Success: true,
          requestId: "test-delete-request-id",
        },
        statusCode: 200,
      };
      mockClient.deleteContext.resolves(mockResponse);

      // Call the method
      const result = await mockContextService.delete(context);

      // Verify OperationResult structure
      expect(result.success).toBe(true);
      expect(result.requestId).toBe("test-delete-request-id");
      expect(result.data).toBe(true);
      expect(result.errorMessage).toBe("");

      expect(mockClient.deleteContext.calledOnce).toBe(true);
    });
  });

  describe("test_delete_context_failure", () => {
    it("should handle delete context failure", async () => {
      const context = new Context("context-id", "context-name", "available");

      mockClient.deleteContext.rejects(new Error("API Error"));

      const result = await mockContextService.delete(context);

      // Verify error result structure
      expect(result.success).toBe(false);
      expect(result.requestId).toBe("");
      expect(result.errorMessage).toContain("Failed to delete context");
    });
  });
});
