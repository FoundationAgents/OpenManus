import { Context, ContextService, ContextListParams } from "../../src/context";
import * as sinon from "sinon";

describe("TestContextPagination", () => {
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

  describe("test_list_contexts_with_default_params", () => {
    it("should list contexts with default pagination parameters", async () => {
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
          nextToken: "next-page-token",
          maxResults: 10,
          totalCount: 15,
          requestId: "test-list-request-id",
        },
        statusCode: 200,
      };

      mockClient.listContexts.resolves(mockResponse);

      // Call the method with default params (undefined)
      const result = await mockContextService.list(undefined);

      // Verify the API was called with default parameters
      expect(mockClient.listContexts.calledOnce).toBe(true);
      const callArgs = mockClient.listContexts.getCall(0).args[0];
      expect(callArgs.maxResults).toBe(10);
      expect(callArgs.nextToken).toBeUndefined();

      // Verify ContextListResult structure
      expect(result.success).toBe(true);
      expect(result.requestId).toBe("test-list-request-id");
      expect(result.contexts).toHaveLength(2);
      expect(result.errorMessage).toBeUndefined();
      expect(result.nextToken).toBe("next-page-token");
      expect(result.maxResults).toBe(10);
      expect(result.totalCount).toBe(15);

      expect(result.contexts[0].id).toBe("context-1");
      expect(result.contexts[0].name).toBe("context-1-name");
      expect(result.contexts[0].state).toBe("available");
      expect(result.contexts[1].id).toBe("context-2");
      expect(result.contexts[1].name).toBe("context-2-name");
      expect(result.contexts[1].state).toBe("in-use");
    });
  });

  describe("test_list_contexts_with_custom_params", () => {
    it("should list contexts with custom pagination parameters", async () => {
      // Mock the response from the API
      const mockResponse = {
        body: {
          data: [
            {
              id: "context-3",
              name: "context-3-name",
              state: "available",
              createTime: "2025-05-29T14:00:00Z",
              lastUsedTime: "2025-05-29T14:30:00Z",
              osType: "linux",
            },
            {
              id: "context-4",
              name: "context-4-name",
              state: "in-use",
              createTime: "2025-05-29T15:00:00Z",
              lastUsedTime: "2025-05-29T15:30:00Z",
              osType: "windows",
            },
            {
              id: "context-5",
              name: "context-5-name",
              state: "available",
              createTime: "2025-05-29T16:00:00Z",
              lastUsedTime: "2025-05-29T16:30:00Z",
              osType: "macos",
            },
          ],
          nextToken: "another-page-token",
          maxResults: 5,
          totalCount: 15,
          requestId: "test-list-request-id",
        },
        statusCode: 200,
      };

      mockClient.listContexts.resolves(mockResponse);

      // Create custom params
      const params: ContextListParams = {
        maxResults: 5,
        nextToken: "page-token"
      };

      // Call the method with custom params
      const result = await mockContextService.list(params);

      // Verify the API was called with custom parameters
      expect(mockClient.listContexts.calledOnce).toBe(true);
      const callArgs = mockClient.listContexts.getCall(0).args[0];
      expect(callArgs.maxResults).toBe(5);
      expect(callArgs.nextToken).toBe("page-token");

      // Verify ContextListResult structure
      expect(result.success).toBe(true);
      expect(result.requestId).toBe("test-list-request-id");
      expect(result.contexts).toHaveLength(3);
      expect(result.errorMessage).toBeUndefined();
      expect(result.nextToken).toBe("another-page-token");
      expect(result.maxResults).toBe(5);
      expect(result.totalCount).toBe(15);

      expect(result.contexts[0].id).toBe("context-3");
      expect(result.contexts[1].id).toBe("context-4");
      expect(result.contexts[2].id).toBe("context-5");
    });
  });

  describe("test_list_contexts_with_partial_params", () => {
    it("should list contexts with partial pagination parameters", async () => {
      // Mock the response from the API
      const mockResponse = {
        body: {
          data: [
            {
              id: "context-6",
              name: "context-6-name",
              state: "available",
              createTime: "2025-05-29T17:00:00Z",
              lastUsedTime: "2025-05-29T17:30:00Z",
              osType: "linux",
            },
          ],
          nextToken: "",
          maxResults: 20,
          totalCount: 1,
          requestId: "test-list-request-id",
        },
        statusCode: 200,
      };

      mockClient.listContexts.resolves(mockResponse);

      // Create partial params (only maxResults)
      const params: ContextListParams = {
        maxResults: 20
      };

      // Call the method with partial params
      const result = await mockContextService.list(params);

      // Verify the API was called with partial parameters
      expect(mockClient.listContexts.calledOnce).toBe(true);
      const callArgs = mockClient.listContexts.getCall(0).args[0];
      expect(callArgs.maxResults).toBe(20);
      expect(callArgs.nextToken).toBeUndefined();

      // Verify ContextListResult structure
      expect(result.success).toBe(true);
      expect(result.requestId).toBe("test-list-request-id");
      expect(result.contexts).toHaveLength(1);
      expect(result.errorMessage).toBeUndefined();
      expect(result.nextToken).toBe("");
      expect(result.maxResults).toBe(20);
      expect(result.totalCount).toBe(1);

      expect(result.contexts[0].id).toBe("context-6");
    });
  });

  describe("test_list_contexts_failure", () => {
    it("should handle list contexts failure", async () => {
      mockClient.listContexts.rejects(new Error("API Error"));

      const result = await mockContextService.list(undefined);

      // Verify error result structure
      expect(result.success).toBe(false);
      expect(result.requestId).toBe("");
      expect(result.contexts).toEqual([]);
      expect(result.nextToken).toBeUndefined();
      expect(result.maxResults).toBeUndefined();
      expect(result.totalCount).toBeUndefined();
    });
  });
});