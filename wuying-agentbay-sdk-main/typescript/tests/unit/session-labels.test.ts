import { Session, ListSessionParams } from "../../src";
import { APIError } from "../../src/exceptions";
import * as sinon from "sinon";

describe("Session Labels", () => {
  let mockSession: Session;
  let mockAgentBay: any;
  let mockClient: any;
  let sandbox: sinon.SinonSandbox;
  let labels: Record<string, string>;

  beforeEach(() => {
    sandbox = sinon.createSandbox();

    mockClient = {
      setLabel: sandbox.stub(),
      getLabel: sandbox.stub(),
      releaseMcpSession: sandbox.stub(),
    };

    mockAgentBay = {
      getAPIKey: sandbox.stub().returns("test-api-key"),
      getClient: sandbox.stub().returns(mockClient),
      removeSession: sandbox.stub(),
      create: sandbox.stub(),
      delete: sandbox.stub(),
      listByLabels: sandbox.stub(),
    };

    mockSession = new Session(mockAgentBay, "test-session-id");

    labels = {
      environment: "testing-12345",
      version: "1.0.0",
      project: "labels-test-12345",
      onwer: "test-team-12345",
    };
  });

  afterEach(() => {
    sandbox.restore();
  });

  describe("setLabels()", () => {
    it("should set labels for a session successfully", async () => {
      // Mock setLabel response
      const mockSetLabelsResponse = {
        body: {
          requestId: "set-labels-request-id",
        },
        statusCode: 200,
      };
      mockClient.setLabel.resolves(mockSetLabelsResponse);

      // Call the method
      const setLabelsResponse = await mockSession.setLabels(labels);

      // Verify OperationResult structure
      expect(setLabelsResponse.success).toBe(true);
      expect(setLabelsResponse.requestId).toBe("set-labels-request-id");
      expect(typeof setLabelsResponse.requestId).toBe("string");
      expect(setLabelsResponse.errorMessage).toBeUndefined();

      // Verify API was called correctly
      expect(mockClient.setLabel.calledOnce).toBe(true);
      const callArgs = mockClient.setLabel.getCall(0).args[0];
      expect(callArgs.sessionId).toBe("test-session-id");
      expect(JSON.parse(callArgs.labels)).toEqual(labels);
    });

    it("should handle setLabels failure", async () => {
      // Mock setLabel to reject
      mockClient.setLabel.rejects(new Error("API Error"));

      // Call the method and expect error
      await expect(mockSession.setLabels(labels)).rejects.toThrow(
        "Failed to set labels for session test-session-id"
      );
    });
  });

  describe("getLabels()", () => {
    it("should get labels for a session successfully", async () => {
      // Mock getLabel response
      const mockGetLabelsResponse = {
        body: {
          data: {
            labels: JSON.stringify(labels),
          },
          requestId: "get-labels-request-id",
        },
        statusCode: 200,
      };
      mockClient.getLabel.resolves(mockGetLabelsResponse);

      // Call the method
      const getLabelsResponse = await mockSession.getLabels();

      // Verify OperationResult structure
      expect(getLabelsResponse.success).toBe(true);
      expect(getLabelsResponse.requestId).toBe("get-labels-request-id");
      expect(typeof getLabelsResponse.requestId).toBe("string");
      expect(getLabelsResponse.data).toEqual(labels);
      expect(getLabelsResponse.errorMessage).toBeUndefined();

      // Verify API was called correctly
      expect(mockClient.getLabel.calledOnce).toBe(true);
      const callArgs = mockClient.getLabel.getCall(0).args[0];
      expect(callArgs.sessionId).toBe("test-session-id");
    });

    it("should return empty object if no labels", async () => {
      // Mock getLabel response for empty labels
      const mockGetEmptyLabelsResponse = {
        body: {
          data: {},
          requestId: "get-empty-labels-request-id",
        },
        statusCode: 200,
      };
      mockClient.getLabel.resolves(mockGetEmptyLabelsResponse);

      // Call the method
      const getLabelsResponse = await mockSession.getLabels();

      // Verify OperationResult structure
      expect(getLabelsResponse.success).toBe(true);
      expect(getLabelsResponse.requestId).toBe("get-empty-labels-request-id");
      expect(typeof getLabelsResponse.requestId).toBe("string");
      expect(getLabelsResponse.data).toEqual({});
      expect(getLabelsResponse.errorMessage).toBeUndefined();
    });

    it("should handle getLabels failure", async () => {
      // Mock getLabel to reject
      mockClient.getLabel.rejects(new Error("API Error"));

      // Call the method and expect error
      await expect(mockSession.getLabels()).rejects.toThrow(
        "Failed to get labels for session test-session-id"
      );
    });
  });

  describe("combined setLabels and getLabels", () => {
    it("should set and then retrieve labels", async () => {
      // Mock setLabel response
      const mockSetLabelsResponse = {
        body: {
          requestId: "set-labels-request-id",
        },
        statusCode: 200,
      };
      mockClient.setLabel.resolves(mockSetLabelsResponse);

      // Mock getLabel response for verification
      const mockGetLabelsResponse = {
        body: {
          data: {
            labels: JSON.stringify(labels),
          },
          requestId: "get-labels-request-id",
        },
        statusCode: 200,
      };
      mockClient.getLabel.resolves(mockGetLabelsResponse);

      // First set labels
      const setLabelsResponse = await mockSession.setLabels(labels);
      expect(setLabelsResponse.success).toBe(true);
      expect(setLabelsResponse.requestId).toBe("set-labels-request-id");

      // Then get labels to verify
      const retrievedLabelsResponse = await mockSession.getLabels();
      expect(retrievedLabelsResponse.success).toBe(true);
      expect(retrievedLabelsResponse.data).toEqual(labels);
      expect(retrievedLabelsResponse.requestId).toBe("get-labels-request-id");
    });
  });

  describe("listByLabels()", () => {
    it("should list sessions filtered by labels", async () => {
      // Mock setLabel response
      const mockSetLabelsResponse = {
        body: {
          requestId: "set-labels-request-id",
        },
        statusCode: 200,
      };
      mockClient.setLabel.resolves(mockSetLabelsResponse);

      // Mock listByLabels response using new API format
      const mockListByLabelsResponse = {
        success: true,
        data: [
          { sessionId: "test-session-id", labels: labels },
          { sessionId: "other-session-id", labels: labels },
        ],
        requestId: "list-by-labels-request-id",
        maxResults: 5,
        totalCount: 2,
      };
      mockAgentBay.listByLabels.resolves(mockListByLabelsResponse);

      // First set some unique labels on our session
      const setLabelsResponse = await mockSession.setLabels(labels);
      expect(setLabelsResponse.success).toBe(true);
      expect(setLabelsResponse.requestId).toBe("set-labels-request-id");

      // Then list sessions with those labels using new API format
      const listParams: ListSessionParams = {
        labels: labels,
        maxResults: 5,
      };
      const listByLabelsResponse = await mockAgentBay.listByLabels(listParams);

      // Verify that the response contains requestId and success
      expect(listByLabelsResponse.success).toBe(true);
      expect(listByLabelsResponse.requestId).toBe("list-by-labels-request-id");
      expect(typeof listByLabelsResponse.requestId).toBe("string");

      // Verify pagination info
      expect(listByLabelsResponse.maxResults).toBe(5);
      expect(listByLabelsResponse.totalCount).toBe(2);

      // We should find at least our session
      expect(listByLabelsResponse.data.length).toBeGreaterThan(0);

      // Check if our session is in the results
      const foundSession = listByLabelsResponse.data.some(
        (s: any) => s.sessionId === "test-session-id"
      );
      expect(foundSession).toBe(true);

      listByLabelsResponse.data.forEach((sessionItem: any) => {
        expect(sessionItem).toHaveProperty("sessionId");
        expect(sessionItem.sessionId).toBeTruthy();
      });
    });

    it("should handle non-matching labels", async () => {
      // Use a label that shouldn't match any sessions
      const nonMatchingLabels = {
        nonexistent: "label-unique-12345",
      };

      // Mock listByLabels response for non-matching labels using new API format
      const mockListByLabelsResponse = {
        success: true,
        data: [],
        requestId: "list-non-matching-labels-request-id",
        maxResults: 5,
        totalCount: 0,
      };
      mockAgentBay.listByLabels.resolves(mockListByLabelsResponse);

      const listParams: ListSessionParams = {
        labels: nonMatchingLabels,
        maxResults: 5,
      };
      const listByLabelsResponse = await mockAgentBay.listByLabels(listParams);

      // Verify that the response contains requestId and success
      expect(listByLabelsResponse.success).toBe(true);
      expect(listByLabelsResponse.requestId).toBe(
        "list-non-matching-labels-request-id"
      );
      expect(typeof listByLabelsResponse.requestId).toBe("string");

      // Verify pagination info
      expect(listByLabelsResponse.maxResults).toBe(5);
      expect(listByLabelsResponse.totalCount).toBe(0);

      // There shouldn't be any matching sessions
      expect(listByLabelsResponse.data.length).toBe(0);
    });
  });
});
