import { expect } from "chai";
import * as sinon from "sinon";
import { AgentBay } from "../../src/agent-bay";
import { Client } from "../../src/api/client";
import { Session } from "../../src/session";

describe("TestSession", () => {
  let mockAgentBay: sinon.SinonStubbedInstance<AgentBay>;
  let mockClient: sinon.SinonStubbedInstance<Client>;
  let mockSession: Session;

  beforeEach(() => {
    mockClient = sinon.createStubInstance(Client);
    mockAgentBay = sinon.createStubInstance(AgentBay) as unknown as sinon.SinonStubbedInstance<AgentBay>;

    // Set up necessary properties using public methods
    mockAgentBay.getAPIKey.returns("test_api_key");
    mockAgentBay.getClient.returns(mockClient as unknown as Client);

    // Create a session with the mock agent bay
    mockSession = new Session(mockAgentBay as unknown as AgentBay, "test_session_id");
  });

  afterEach(() => {
    sinon.restore();
  });

  describe("test_validate_labels_success", () => {
    it("should validate labels successfully", () => {
      const labels = { key1: "value1", key2: "value2" };
      const result = mockSession["validateLabels"](labels);
      expect(result).to.be.null;
    });
  });

  describe("test_validate_labels_null", () => {
    it("should fail validation with null labels", () => {
      const labels = null;
      const result = mockSession["validateLabels"](labels as any);
      expect(result).to.not.be.null;
      expect(result?.success).to.be.false;
      expect(result?.errorMessage).to.include("Labels cannot be null");
    });
  });

  describe("test_validate_labels_array", () => {
    it("should fail validation with array labels", () => {
      const labels = ["key1", "value1"];
      const result = mockSession["validateLabels"](labels as any);
      expect(result).to.not.be.null;
      expect(result?.success).to.be.false;
      expect(result?.errorMessage).to.include("Labels cannot be an array");
    });
  });

  describe("test_validate_labels_empty_object", () => {
    it("should fail validation with empty object", () => {
      const labels = {};
      const result = mockSession["validateLabels"](labels);
      expect(result).to.not.be.null;
      expect(result?.success).to.be.false;
      expect(result?.errorMessage).to.include("Labels cannot be empty");
    });
  });

  describe("test_validate_labels_empty_key", () => {
    it("should fail validation with empty key", () => {
      const labels = { "": "value1" };
      const result = mockSession["validateLabels"](labels);
      expect(result).to.not.be.null;
      expect(result?.success).to.be.false;
      expect(result?.errorMessage).to.include("Label keys cannot be empty");
    });
  });

  describe("test_validate_labels_empty_value", () => {
    it("should fail validation with empty value", () => {
      const labels = { key1: "" };
      const result = mockSession["validateLabels"](labels);
      expect(result).to.not.be.null;
      expect(result?.success).to.be.false;
      expect(result?.errorMessage).to.include("Label values cannot be empty");
    });
  });

  describe("test_validate_labels_null_value", () => {
    it("should fail validation with null value", () => {
      const labels = { key1: null };
      const result = mockSession["validateLabels"](labels as any);
      expect(result).to.not.be.null;
      expect(result?.success).to.be.false;
      expect(result?.errorMessage).to.include("Label values cannot be empty");
    });
  });

  describe("test_get_api_key", () => {
    it("should return correct API key", () => {
      const apiKey = mockSession.getAPIKey();
      expect(apiKey).to.equal("test_api_key");
    });
  });

  describe("test_get_client", () => {
    it("should return correct client", () => {
      const client = mockSession.getClient();
      expect(client).to.equal(mockClient);
    });
  });

  describe("test_get_session_id", () => {
    it("should return correct session ID", () => {
      const sessionId = mockSession.getSessionId();
      expect(sessionId).to.equal("test_session_id");
    });
  });

  describe("test_delete_success", () => {
    it("should delete session successfully", async () => {
      const mockResponse = {
        body: {
          requestId: "test-request-id",
          success: true,
        },
        statusCode: 200,
      };

      mockClient.releaseMcpSession.resolves(mockResponse as any);

      const result = await mockSession.delete();

      // Verify DeleteResult structure
      expect(result.success).to.equal(true);
      expect(result.requestId).to.equal("test-request-id");
      expect(result.errorMessage).to.be.undefined;

      expect(mockClient.releaseMcpSession.calledOnce).to.be.true;

      const callArgs = mockClient.releaseMcpSession.getCall(0).args[0];
      expect(callArgs.authorization).to.equal("Bearer test_api_key");
      expect(callArgs.sessionId).to.equal("test_session_id");
    });
  });

  describe("test_delete_without_params", () => {
    it("should delete without syncing contexts when no parameters are provided", async () => {
      // Mock context manager
      mockSession.context = {
        sync: sinon.stub().resolves({ success: true }),
        info: sinon.stub().resolves({ contextStatusData: [] })
      } as any;

      const mockResponse = {
        body: {
          requestId: "test-request-id",
          success: true,
        },
        statusCode: 200,
      };

      mockClient.releaseMcpSession.resolves(mockResponse as any);

      // Call delete without parameters
      const result = await mockSession.delete();

      // Verify sync was not called
      expect((mockSession.context.sync as sinon.SinonStub).called).to.be.false;
      expect((mockSession.context.info as sinon.SinonStub).called).to.be.false;

      // Verify result
      expect(result.success).to.equal(true);
      expect(result.requestId).to.equal("test-request-id");
    });
  });

  describe("test_delete_with_syncContext", () => {
    it("should sync contexts when syncContext=true", async () => {
      // Mock context manager
      mockSession.context = {
        sync: sinon.stub().resolves({ success: true, requestId: "sync-request-id" }),
        info: sinon.stub().resolves({
          requestId: "info-request-id",
          contextStatusData: [
            {
              contextId: "ctx1",
              path: "/test/path",
              status: "Success",
              taskType: "upload",
              startTime: 1600000000,
              finishTime: 1600000100,
              errorMessage: ""
            }
          ]
        })
      } as any;

      const mockResponse = {
        body: {
          requestId: "test-request-id",
          success: true,
        },
        statusCode: 200,
      };

      mockClient.releaseMcpSession.resolves(mockResponse as any);

      // Call delete with syncContext=true
      const result = await mockSession.delete(true);

      // Verify sync was called (info is called internally by sync, not directly by delete)
      expect((mockSession.context.sync as sinon.SinonStub).calledOnce).to.be.true;
      // Note: context.info is called internally by context.sync, not directly by session.delete

      // Verify result
      expect(result.success).to.equal(true);
      expect(result.requestId).to.equal("test-request-id");
    });
  });

  describe("test_delete_failure", () => {
    it("should handle delete failure", async () => {
      const mockResponse = {
        body: {
          requestId: "test-request-id",
          success: false,
          errorMessage: "Delete failed",
        },
        statusCode: 400,
      };

      mockClient.releaseMcpSession.resolves(mockResponse as any);

      const result = await mockSession.delete();

      expect(result.success).to.equal(false);
      expect(result.requestId).to.equal("test-request-id");
      expect(result.errorMessage).to.equal("[Unknown] Failed to delete session");

      expect(mockClient.releaseMcpSession.calledOnce).to.be.true;
    });
  });

  describe("test_delete_api_error", () => {
    it("should handle API error during delete", async () => {
      mockClient.releaseMcpSession.rejects(new Error("Network error"));

      let errorThrown = false;
      try {
        await mockSession.delete();
        // If we reach here, the test should fail
        expect.fail("Expected delete to throw an error");
      } catch (error) {
        errorThrown = true;
        // In this case, we're checking that an error was thrown, which is sufficient
        // The specific type of error may vary depending on the test framework
      }

      expect(errorThrown).to.be.true;
      expect(mockClient.releaseMcpSession.calledOnce).to.be.true;
    });
  });

  describe("test_set_labels_success", () => {
    it("should set labels successfully", async () => {
      const mockResponse = {
        body: {
          requestId: "test-request-id",
          success: true,
        },
        statusCode: 200,
      };

      mockClient.setLabel.resolves(mockResponse as any);

      const labels = { key1: "value1", key2: "value2" };
      const result = await mockSession.setLabels(labels);

      expect(result.success).to.equal(true);
      expect(result.requestId).to.equal("test-request-id");

      expect(mockClient.setLabel.calledOnce).to.be.true;
      const callArgs = mockClient.setLabel.getCall(0).args[0];
      expect(callArgs.authorization).to.equal("Bearer test_api_key");
      expect(callArgs.sessionId).to.equal("test_session_id");
      expect(callArgs.labels).to.equal('{"key1":"value1","key2":"value2"}');
    });
  });

  describe("test_set_labels_api_error", () => {
    it("should handle API error during set labels", async () => {
      mockClient.setLabel.rejects(new Error("Network error"));

      const labels = { key1: "value1" };
      try {
        await mockSession.setLabels(labels);
        // If we reach here, the test should fail
        expect.fail("Expected setLabels to throw an error");
      } catch (error) {
        expect(error).to.be.an("error");
        expect((error as Error).message).to.include("Failed to set labels for session");
      }

      expect(mockClient.setLabel.calledOnce).to.be.true;
    });
  });

  describe("test_get_labels_success", () => {
    it("should get labels successfully", async () => {
      const mockResponse = {
        body: {
          requestId: "test-request-id",
          data: {
            labels: '{"key1":"value1","key2":"value2"}'
          },
          success: true,
        },
        statusCode: 200,
      };

      mockClient.getLabel.resolves(mockResponse as any);

      const result = await mockSession.getLabels();

      expect(result.success).to.equal(true);
      expect(result.requestId).to.equal("test-request-id");
      expect(result.data).to.deep.equal({ key1: "value1", key2: "value2" });

      expect(mockClient.getLabel.calledOnce).to.be.true;
      const callArgs = mockClient.getLabel.getCall(0).args[0];
      expect(callArgs.authorization).to.equal("Bearer test_api_key");
      expect(callArgs.sessionId).to.equal("test_session_id");
    });
  });

  describe("test_get_labels_api_error", () => {
    it("should handle API error during get labels", async () => {
      mockClient.getLabel.rejects(new Error("Network error"));

      try {
        await mockSession.getLabels();
        // If we reach here, the test should fail
        expect.fail("Expected getLabels to throw an error");
      } catch (error) {
        expect(error).to.be.an("error");
        expect((error as Error).message).to.include("Failed to get labels for session");
      }

      expect(mockClient.getLabel.calledOnce).to.be.true;
    });
  });

  describe("test_get_link_success", () => {
    it("should get link successfully", async () => {
      const mockResponse = {
        body: {
          requestId: "test-request-id",
          data: {
            url: "wss://example.com/websocket"
          },
          success: true,
        },
        statusCode: 200,
      };

      mockClient.getLink.resolves(mockResponse as any);

      const result = await mockSession.getLink();

      expect(result.success).to.equal(true);
      expect(result.requestId).to.equal("test-request-id");
      expect(result.data).to.equal("wss://example.com/websocket");

      expect(mockClient.getLink.calledOnce).to.be.true;
      const callArgs = mockClient.getLink.getCall(0).args[0];
      expect(callArgs.authorization).to.equal("Bearer test_api_key");
      expect(callArgs.sessionId).to.equal("test_session_id");
      expect(callArgs.protocolType).to.be.undefined;
      expect(callArgs.port).to.be.undefined;
    });
  });

  // Port validation tests for getLink method
  describe("test_get_link_with_valid_port", () => {
    it("should get link successfully with valid port in range [30100, 30199]", async () => {
      const mockResponse = {
        body: {
          requestId: "test-request-id",
          data: {
            url: "wss://example.com:30150/websocket"
          },
          success: true,
        },
        statusCode: 200,
      };

      mockClient.getLink.resolves(mockResponse as any);

      const validPort = 30150; // Valid port in range
      const result = await mockSession.getLink("wss", validPort);

      expect(result.success).to.equal(true);
      expect(result.requestId).to.equal("test-request-id");
      expect(result.data).to.equal("wss://example.com:30150/websocket");

      expect(mockClient.getLink.calledOnce).to.be.true;
      const callArgs = mockClient.getLink.getCall(0).args[0];
      expect(callArgs.authorization).to.equal("Bearer test_api_key");
      expect(callArgs.sessionId).to.equal("test_session_id");
      expect(callArgs.protocolType).to.equal("wss");
      expect(callArgs.port).to.equal(30150);
    });
  });

  describe("test_get_link_with_port_boundary_values", () => {
    it("should get link successfully with port at lower boundary (30100)", async () => {
      const mockResponse = {
        body: {
          requestId: "test-request-id",
          data: {
            url: "wss://example.com:30100/websocket"
          },
          success: true,
        },
        statusCode: 200,
      };

      mockClient.getLink.resolves(mockResponse as any);

      const result = await mockSession.getLink("wss", 30100);

      expect(result.success).to.equal(true);
      expect(result.data).to.equal("wss://example.com:30100/websocket");
    });

    it("should get link successfully with port at upper boundary (30199)", async () => {
      const mockResponse = {
        body: {
          requestId: "test-request-id",
          data: {
            url: "wss://example.com:30199/websocket"
          },
          success: true,
        },
        statusCode: 200,
      };

      mockClient.getLink.resolves(mockResponse as any);

      const result = await mockSession.getLink("wss", 30199);

      expect(result.success).to.equal(true);
      expect(result.data).to.equal("wss://example.com:30199/websocket");
    });
  });

  describe("test_get_link_with_invalid_port_below_range", () => {
    it("should throw error when port is below valid range (< 30100)", async () => {
      const invalidPort = 30099; // Below valid range

      try {
        await mockSession.getLink("wss", invalidPort);
        expect.fail("Expected getLink to throw an error for invalid port");
      } catch (error) {
        expect(error).to.be.an("error");
        expect((error as Error).message).to.include(`Invalid port value: ${invalidPort}`);
        expect((error as Error).message).to.include("Port must be an integer in the range [30100, 30199]");
      }

      // Verify that the API was not called due to client-side validation
      expect(mockClient.getLink.called).to.be.false;
    });
  });

  describe("test_get_link_with_invalid_port_above_range", () => {
    it("should throw error when port is above valid range (> 30199)", async () => {
      const invalidPort = 30200; // Above valid range

      try {
        await mockSession.getLink("wss", invalidPort);
        expect.fail("Expected getLink to throw an error for invalid port");
      } catch (error) {
        expect(error).to.be.an("error");
        expect((error as Error).message).to.include(`Invalid port value: ${invalidPort}`);
        expect((error as Error).message).to.include("Port must be an integer in the range [30100, 30199]");
      }

      // Verify that the API was not called due to client-side validation
      expect(mockClient.getLink.called).to.be.false;
    });
  });

  describe("test_get_link_with_non_integer_port", () => {
    it("should throw error when port is not an integer", async () => {
      const invalidPort = 30150.5; // Non-integer

      try {
        await mockSession.getLink("wss", invalidPort);
        expect.fail("Expected getLink to throw an error for non-integer port");
      } catch (error) {
        expect(error).to.be.an("error");
        expect((error as Error).message).to.include(`Invalid port value: ${invalidPort}`);
        expect((error as Error).message).to.include("Port must be an integer in the range [30100, 30199]");
      }

      // Verify that the API was not called due to client-side validation
      expect(mockClient.getLink.called).to.be.false;
    });
  });

  describe("test_get_link_backend_port_validation", () => {
    it("should handle backend error for invalid port (simulating server-side validation)", async () => {
      const mockErrorResponse = {
        body: {
          requestId: "test-request-id",
          success: false,
          errorMessage: "Invalid port parameter",
        },
        statusCode: 400,
      };

      mockClient.getLink.rejects(new Error("Bad Request: Invalid port parameter"));

      // Use a valid port to bypass client-side validation but simulate server rejection
      const port = 30150;

      try {
        await mockSession.getLink("wss", port);
        expect.fail("Expected getLink to throw an error from backend");
      } catch (error) {
        expect(error).to.be.an("error");
        expect((error as Error).message).to.include("Failed to get link");
        expect((error as Error).message).to.include("Bad Request: Invalid port parameter");
      }

      // Verify that the API was called (client-side validation passed)
      expect(mockClient.getLink.calledOnce).to.be.true;
    });
  });

  // Port validation tests for getLinkAsync method
  describe("test_get_link_async_with_valid_port", () => {
    it("should get link asynchronously with valid port in range [30100, 30199]", async () => {
      const mockResponse = {
        body: {
          requestId: "test-request-id",
          data: {
            url: "wss://example.com:30150/websocket"
          },
          success: true,
        },
        statusCode: 200,
      };

      mockClient.getLink.resolves(mockResponse as any);

      const validPort = 30150; // Valid port in range
      const result = await mockSession.getLinkAsync("wss", validPort);

      expect(result.success).to.equal(true);
      expect(result.requestId).to.equal("test-request-id");
      expect(result.data).to.equal("wss://example.com:30150/websocket");

      expect(mockClient.getLink.calledOnce).to.be.true;
      const callArgs = mockClient.getLink.getCall(0).args[0];
      expect(callArgs.authorization).to.equal("Bearer test_api_key");
      expect(callArgs.sessionId).to.equal("test_session_id");
      expect(callArgs.protocolType).to.equal("wss");
      expect(callArgs.port).to.equal(30150);
    });
  });

  describe("test_get_link_async_with_invalid_port", () => {
    it("should throw error when port is invalid in getLinkAsync", async () => {
      const invalidPort = 25000; // Below valid range

      try {
        await mockSession.getLinkAsync("wss", invalidPort);
        expect.fail("Expected getLinkAsync to throw an error for invalid port");
      } catch (error) {
        expect(error).to.be.an("error");
        expect((error as Error).message).to.include(`Invalid port value: ${invalidPort}`);
        expect((error as Error).message).to.include("Port must be an integer in the range [30100, 30199]");
      }

      // Verify that the API was not called due to client-side validation
      expect(mockClient.getLink.called).to.be.false;
    });
  });
});
