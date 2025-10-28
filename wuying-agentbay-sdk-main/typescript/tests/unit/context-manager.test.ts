import * as sinon from "sinon";
import { ContextManager, SessionInterface } from "../../src/context-manager";

describe("ContextManager", () => {
  let contextManager: ContextManager;
  let mockSession: SessionInterface;
  let mockClient: any;
  let sandbox: sinon.SinonSandbox;

  beforeEach(() => {
    sandbox = sinon.createSandbox();

    mockClient = {
      getContextInfo: sandbox.stub(),
      syncContext: sandbox.stub(),
    };

    mockSession = {
      getAPIKey: sandbox.stub().returns("test-api-key"),
      getClient: sandbox.stub().returns(mockClient),
      getSessionId: sandbox.stub().returns("test-session-id"),
    };

    contextManager = new ContextManager(mockSession);
  });

  afterEach(() => {
    sandbox.restore();
  });

  describe("info", () => {
    it("should parse context status data correctly", async () => {
      // Create a sample context status JSON response
      const contextStatusStr = '[{"type":"data","data":"[{\\"contextId\\":\\"ctx-123\\",\\"path\\":\\"/home/user\\",\\"errorMessage\\":\\"\\",\\"status\\":\\"Success\\",\\"startTime\\":1600000000,\\"finishTime\\":1600000100,\\"taskType\\":\\"download\\"}]"}]';
      
      // Mock the API response
      const mockResponse = {
        body: {
          data: {
            contextStatus: contextStatusStr
          },
          requestId: "test-request-id"
        },
        statusCode: 200
      };
      
      mockClient.getContextInfo.resolves(mockResponse);
      
      // Call the method
      const result = await contextManager.info();
      
      // Verify the results
      expect(result.requestId).toBe("test-request-id");
      expect(result.contextStatusData).toHaveLength(1);
      
      // Check the parsed data
      const statusData = result.contextStatusData[0];
      expect(statusData.contextId).toBe("ctx-123");
      expect(statusData.path).toBe("/home/user");
      expect(statusData.errorMessage).toBe("");
      expect(statusData.status).toBe("Success");
      expect(statusData.startTime).toBe(1600000000);
      expect(statusData.finishTime).toBe(1600000100);
      expect(statusData.taskType).toBe("download");
      
      // Verify the API was called correctly
      expect(mockClient.getContextInfo.calledOnce).toBe(true);
      const callArgs = mockClient.getContextInfo.firstCall.args[0];
      expect(callArgs.authorization).toBe("Bearer test-api-key");
      expect(callArgs.sessionId).toBe("test-session-id");
    });

    it("should handle multiple context status items", async () => {
      // Create a sample context status JSON response with multiple items
      const contextStatusStr = '[{"type":"data","data":"[{\\"contextId\\":\\"ctx-123\\",\\"path\\":\\"/home/user\\",\\"errorMessage\\":\\"\\",\\"status\\":\\"Success\\",\\"startTime\\":1600000000,\\"finishTime\\":1600000100,\\"taskType\\":\\"download\\"},{\\"contextId\\":\\"ctx-456\\",\\"path\\":\\"/home/user/docs\\",\\"errorMessage\\":\\"\\",\\"status\\":\\"Success\\",\\"startTime\\":1600000200,\\"finishTime\\":1600000300,\\"taskType\\":\\"upload\\"}]"}]';
      
      // Mock the API response
      const mockResponse = {
        body: {
          data: {
            contextStatus: contextStatusStr
          },
          requestId: "test-request-id"
        },
        statusCode: 200
      };
      
      mockClient.getContextInfo.resolves(mockResponse);
      
      // Call the method
      const result = await contextManager.info();
      
      // Verify the results
      expect(result.requestId).toBe("test-request-id");
      expect(result.contextStatusData).toHaveLength(2);
      
      // Check the first item
      const statusData1 = result.contextStatusData[0];
      expect(statusData1.contextId).toBe("ctx-123");
      expect(statusData1.path).toBe("/home/user");
      expect(statusData1.taskType).toBe("download");
      
      // Check the second item
      const statusData2 = result.contextStatusData[1];
      expect(statusData2.contextId).toBe("ctx-456");
      expect(statusData2.path).toBe("/home/user/docs");
      expect(statusData2.taskType).toBe("upload");
    });

    it("should handle empty response", async () => {
      // Mock the API response with empty data
      const mockResponse = {
        body: {
          data: {},
          requestId: "test-request-id"
        },
        statusCode: 200
      };
      
      mockClient.getContextInfo.resolves(mockResponse);
      
      // Call the method
      const result = await contextManager.info();
      
      // Verify the results
      expect(result.requestId).toBe("test-request-id");
      expect(result.contextStatusData).toHaveLength(0);
    });

    it("should handle invalid JSON", async () => {
      // Mock the API response with invalid JSON
      const mockResponse = {
        body: {
          data: {
            contextStatus: "invalid json"
          },
          requestId: "test-request-id"
        },
        statusCode: 200
      };
      
      mockClient.getContextInfo.resolves(mockResponse);
      
      // Call the method
      const result = await contextManager.info();
      
      // Verify the results - should not throw exception but return empty array
      expect(result.requestId).toBe("test-request-id");
      expect(result.contextStatusData).toHaveLength(0);
    });

    it("should handle API error", async () => {
      // Mock API error
      mockClient.getContextInfo.rejects(new Error("API error"));
      
      // Call the method and expect it to throw
      await expect(contextManager.info()).rejects.toThrow("Failed to get context info: Error: API error");
    });

    it("should pass optional parameters correctly", async () => {
      // Mock the API response
      const mockResponse = {
        body: {
          data: {
            contextStatus: '[]'
          },
          requestId: "test-request-id"
        },
        statusCode: 200
      };
      
      mockClient.getContextInfo.resolves(mockResponse);
      
      // Call the method with parameters
      await contextManager.infoWithParams("ctx-123", "/home/user", "download");
      
      // Verify the API was called with the correct parameters
      expect(mockClient.getContextInfo.calledOnce).toBe(true);
      const callArgs = mockClient.getContextInfo.firstCall.args[0];
      expect(callArgs.contextId).toBe("ctx-123");
      expect(callArgs.path).toBe("/home/user");
      expect(callArgs.taskType).toBe("download");
    });
  });

  describe("sync", () => {
    it("should sync context successfully without callback (await mode)", async () => {
      // Mock the API response
      const mockResponse = {
        body: {
          success: true,
          requestId: "test-request-id"
        },
        statusCode: 200
      };
      
      mockClient.syncContext.resolves(mockResponse);
      
      // Mock the info method to return completed status
      const mockInfoResponse = {
        body: {
          data: {
            contextStatus: '[]'
          },
          requestId: "test-request-id"
        },
        statusCode: 200
      };
      mockClient.getContextInfo.resolves(mockInfoResponse);
      
      // Call the method without callback (await mode)
      const result = await contextManager.sync();
      
      // Verify the results
      expect(result.requestId).toBe("test-request-id");
      expect(result.success).toBe(true);
      
      // Verify the API was called correctly
      expect(mockClient.syncContext.calledOnce).toBe(true);
    });

    it("should sync context with callback (async mode)", async () => {
      // Mock the API response
      const mockResponse = {
        body: {
          success: true,
          requestId: "test-request-id"
        },
        statusCode: 200
      };
      
      mockClient.syncContext.resolves(mockResponse);
      
      // Mock the info method to return completed status
      const mockInfoResponse = {
        body: {
          data: {
            contextStatus: '[]'
          },
          requestId: "test-request-id"
        },
        statusCode: 200
      };
      mockClient.getContextInfo.resolves(mockInfoResponse);
      
      // Set up callback
      const callback = sandbox.stub();
      
      // Call the method with callback (async mode)
      const result = await contextManager.sync(undefined, undefined, undefined, callback);
      
      // Verify the results
      expect(result.requestId).toBe("test-request-id");
      expect(result.success).toBe(true);
      
      // Verify the API was called correctly
      expect(mockClient.syncContext.calledOnce).toBe(true);
      
      // Wait for the polling to complete - callback should be called immediately since no sync tasks
      await new Promise(resolve => setTimeout(resolve, 200));
      
      // Verify callback was called
      expect(callback.calledOnce).toBe(true);
      expect(callback.firstCall.args[0]).toBe(true);
    });

    it("should handle API error during sync", async () => {
      // Mock API error
      mockClient.syncContext.rejects(new Error("API error"));
      
      // Call the method and expect it to throw
      await expect(contextManager.sync()).rejects.toThrow("Failed to sync context: Error: API error");
    });

    it("should pass optional parameters correctly for sync", async () => {
      // Mock the API response
      const mockResponse = {
        body: {
          success: true,
          requestId: "test-request-id"
        },
        statusCode: 200
      };
      
      mockClient.syncContext.resolves(mockResponse);
      
      // Mock the info method to return completed status
      const mockInfoResponse = {
        body: {
          data: {
            contextStatus: '[]'
          },
          requestId: "test-request-id"
        },
        statusCode: 200
      };
      mockClient.getContextInfo.resolves(mockInfoResponse);
      
      // Call the method with parameters
      await contextManager.sync("ctx-123", "/home/user", "upload");
      
      // Verify the API was called with the correct parameters
      expect(mockClient.syncContext.calledOnce).toBe(true);
      const callArgs = mockClient.syncContext.firstCall.args[0];
      expect(callArgs.contextId).toBe("ctx-123");
      expect(callArgs.path).toBe("/home/user");
      expect(callArgs.mode).toBe("upload");
    });
  });
}); 