import {
  AgentBay,
  Session,
  AuthenticationError,
  APIError,
  ListSessionParams,
} from "../../src";
import { log } from "../../src/utils/logger";
import * as sinon from "sinon";

// Define Node.js process if it's not available
declare namespace NodeJS {
  interface ProcessEnv {
    [key: string]: string | undefined;
  }
}

declare var process: {
  env: {
    [key: string]: string | undefined;
  };
};

// Mock data for tests
const mockSessionData = {
  sessionId: "mock-session-123",
  resourceUrl: "mock-resource-url",
};

const mockSessionAData = {
  sessionId: "mock-session-a-456",
  resourceUrl: "mock-resource-url-a",
};

const mockSessionBData = {
  sessionId: "mock-session-b-789",
  resourceUrl: "mock-resource-url-b",
};

// Mock config data
const mockConfigData = {
  endpoint: "mock-endpoint",
  timeout_ms: 30000,
};

describe("AgentBay", () => {
  let mockClient: any;
  let createMcpSessionStub: sinon.SinonStub;
  let listSessionStub: sinon.SinonStub;
  let releaseMcpSessionStub: sinon.SinonStub;
  let loadConfigStub: sinon.SinonStub;
  let clientConstructorStub: sinon.SinonStub;
  let contextServiceConstructorStub: sinon.SinonStub;

  beforeEach(() => {
    // Create mock client
    mockClient = {
      createMcpSession: sinon.stub(),
      listSession: sinon.stub(),
      releaseMcpSession: sinon.stub(),
    };

    // Get references to stubs for easier access
    createMcpSessionStub = mockClient.createMcpSession;
    listSessionStub = mockClient.listSession;
    releaseMcpSessionStub = mockClient.releaseMcpSession;

    // Mock loadConfig function
    loadConfigStub = sinon
      .stub(require("../../src/config"), "loadConfig")
      .returns(mockConfigData);

    // Mock Client constructor
    clientConstructorStub = sinon.stub().returns(mockClient);
    sinon
      .stub(require("../../src/api/client"), "Client")
      .callsFake(clientConstructorStub);

    // Mock ContextService constructor
    const mockContextService = {
      get: sinon.stub().resolves({ 
        success: false, 
        errorMessage: 'Context not found' 
      })
    };
    contextServiceConstructorStub = sinon.stub().returns(mockContextService);
    sinon
      .stub(require("../../src/context"), "ContextService")
      .callsFake(contextServiceConstructorStub);

    // Mock AgentBay's getClient method to return our mock client
    sinon.stub(AgentBay.prototype, "getClient").returns(mockClient);

    // Mock Session's getAPIKey method to avoid real API key issues
    sinon.stub(Session.prototype, "getAPIKey").returns("mock-api-key");

    log("Mock client setup complete");
  });

  afterEach(() => {
    sinon.restore();
  });

  describe("constructor", () => {
    it("should initialize with API key from options", () => {
      const apiKey = "test-api-key";
      const agentBay = new AgentBay({ apiKey });
      log(apiKey);

      expect(agentBay.getAPIKey()).toBe(apiKey);

      // Verify that loadConfig was called
      expect(loadConfigStub.calledOnce).toBe(true);

      // Verify that Client was constructed with correct config
      expect(clientConstructorStub.calledOnce).toBe(true);
      const clientConfig = clientConstructorStub.getCall(0).args[0];
      expect(clientConfig.regionId).toBe("");
      expect(clientConfig.endpoint).toBe(mockConfigData.endpoint);
      expect(clientConfig.readTimeout).toBe(mockConfigData.timeout_ms);
      expect(clientConfig.connectTimeout).toBe(mockConfigData.timeout_ms);

      // Verify that ContextService was constructed
      expect(contextServiceConstructorStub.calledOnce).toBe(true);
    });

    it("should initialize with API key from environment variable", () => {
      const originalEnv = process.env.AGENTBAY_API_KEY;
      process.env.AGENTBAY_API_KEY = "env_api_key";

      try {
        const agentBay = new AgentBay();
        expect(agentBay.getAPIKey()).toBe("env_api_key");

        // Verify dependencies were called
        expect(loadConfigStub.called).toBe(true);
        expect(clientConstructorStub.called).toBe(true);
        expect(contextServiceConstructorStub.called).toBe(true);
      } finally {
        // Restore original environment
        if (originalEnv) {
          process.env.AGENTBAY_API_KEY = originalEnv;
        } else {
          delete process.env.AGENTBAY_API_KEY;
        }
      }
    });

    it("should throw AuthenticationError if no API key is provided", () => {
      const originalEnv = process.env.AGENTBAY_API_KEY;
      delete process.env.AGENTBAY_API_KEY;

      try {
        expect(() => new AgentBay()).toThrow(AuthenticationError);
      } finally {
        // Restore original environment
        if (originalEnv) {
          process.env.AGENTBAY_API_KEY = originalEnv;
        }
      }
    });
  });

  describe("create, list, and delete", () => {
    let agentBay: AgentBay;
    let session: Session;

    beforeEach(() => {
      const apiKey = "test-api-key";
      agentBay = new AgentBay({ apiKey });
    });

    it("should create, list, and delete a session with requestId", async () => {
      // Setup mock response for create session
      const createMockResponse = {
        statusCode: 200,
        body: {
          data: mockSessionData,
          requestId: "mock-request-id-create",
        },
      };

      // Setup mock response for delete session
      const deleteMockResponse = {
        statusCode: 200,
        body: {
          requestId: "mock-request-id-delete",
        },
      };

      createMcpSessionStub.resolves(createMockResponse);
      releaseMcpSessionStub.resolves(deleteMockResponse);

      // Verify mock setup before test
      log("Verifying mock setup...");
      expect(createMcpSessionStub).toBeDefined();
      expect(releaseMcpSessionStub).toBeDefined();
      expect(typeof createMcpSessionStub.resolves).toBe("function");

      // Create a session
      log("Creating a new session...");
      const createResponse = await agentBay.create();
      session = createResponse.session!; // Use session field instead of data
      log(`Session created with ID: ${session?.sessionId || 'undefined'}`);
      log(
        `Create Session RequestId: ${createResponse.requestId || "undefined"}`
      );

      // Verify that the mock was called
      expect(createMcpSessionStub.called).toBe(true);
      log(`createMcpSessionStub called: ${createMcpSessionStub.called}`);
      log(`createMcpSessionStub callCount: ${createMcpSessionStub.callCount}`);

      // Verify that the response contains requestId and success
      expect(createResponse.requestId).toBeDefined();
      expect(typeof createResponse.requestId).toBe("string");
      expect(createResponse.requestId).toBe("mock-request-id-create");
      expect(createResponse.success).toBe(true);
      expect(createResponse.session).toBeDefined();

      // Ensure session ID matches mock data
      expect(session.sessionId).toBe(mockSessionData.sessionId);

      // Verify session uses mock client
      expect(session.getClient()).toBe(mockClient);
      log(
        `Session client is mockClient: ${session.getClient() === mockClient}`
      );


      // Delete the session
      log("Deleting the session...");
      const deleteResponse = await agentBay.delete(session);
      log(
        `Delete Session RequestId: ${deleteResponse.requestId || "undefined"}`
      );

      // Verify that the delete mock was called
      expect(releaseMcpSessionStub.called).toBe(true);
      log(`releaseMcpSessionStub called: ${releaseMcpSessionStub.called}`);
      log(
        `releaseMcpSessionStub callCount: ${releaseMcpSessionStub.callCount}`
      );

      // Verify that the delete response contains requestId and success
      expect(deleteResponse.requestId).toBeDefined();
      expect(typeof deleteResponse.requestId).toBe("string");
      expect(deleteResponse.requestId).toBe("mock-request-id-delete");
      expect(deleteResponse.success).toBe(true);

      // Session deletion completed

      // Verify API calls were made with correct parameters
      expect(createMcpSessionStub.calledOnce).toBe(true);
      expect(releaseMcpSessionStub.calledOnce).toBe(true);

      const createCallArgs = createMcpSessionStub.getCall(0).args[0];
      expect(createCallArgs.authorization).toBe("Bearer test-api-key");

      const deleteCallArgs = releaseMcpSessionStub.getCall(0).args[0];
      expect(deleteCallArgs.sessionId).toBe(mockSessionData.sessionId);
      expect(deleteCallArgs.authorization).toBe("Bearer mock-api-key");

      log("All mock verifications passed successfully");
    });
  });

  describe("listByLabels", () => {
    let agentBay: AgentBay;
    let sessionA: Session;
    let sessionB: Session;

    beforeEach(async () => {
      const apiKey = "test-api-key";
      agentBay = new AgentBay({ apiKey });

      // Setup mock responses for creating sessions
      const createMockResponseA = {
        statusCode: 200,
        body: {
          data: mockSessionAData,
          requestId: "mock-request-id-create-a",
        },
      };

      const createMockResponseB = {
        statusCode: 200,
        body: {
          data: mockSessionBData,
          requestId: "mock-request-id-create-b",
        },
      };

      createMcpSessionStub.onFirstCall().resolves(createMockResponseA);
      createMcpSessionStub.onSecondCall().resolves(createMockResponseB);

      const labelsA = {
        environment: "development",
        owner: "team-a",
        project: "project-x",
      };

      const labelsB = {
        environment: "testing",
        owner: "team-b",
        project: "project-y",
      };

      // Create session with labels A
      log("Creating session with labels A...");
      const createResponseA = await agentBay.create({ labels: labelsA });
      sessionA = createResponseA.session!; // Use session field instead of data
      log(`Session created with ID: ${sessionA.sessionId}`);
      log(
        `Create Session A RequestId: ${
          createResponseA.requestId || "undefined"
        }`
      );

      // Create session with labels B
      const createResponseB = await agentBay.create({ labels: labelsB });
      sessionB = createResponseB.session!; // Use session field instead of data
      log(`Session created with ID: ${sessionB.sessionId}`);
      log(
        `Create Session B RequestId: ${
          createResponseB.requestId || "undefined"
        }`
      );
    });

    afterEach(async () => {
      // Clean up sessions
      log("Cleaning up sessions...");

      // Setup mock responses for delete operations
      const deleteMockResponseA = {
        statusCode: 200,
        body: { requestId: "mock-request-id-delete-a" },
      };

      const deleteMockResponseB = {
        statusCode: 200,
        body: { requestId: "mock-request-id-delete-b" },
      };

      // Reset the stub to handle multiple calls
      releaseMcpSessionStub.reset();
      releaseMcpSessionStub.onFirstCall().resolves(deleteMockResponseA);
      releaseMcpSessionStub.onSecondCall().resolves(deleteMockResponseB);

      if (sessionA) {
        try {
          const deleteResponseA = await agentBay.delete(sessionA);
          log(
            `Delete Session A RequestId: ${
              deleteResponseA.requestId || "undefined"
            }`
          );
        } catch (error) {
          log(`Warning: Error deleting session A: ${error}`);
        }
      }

      if (sessionB) {
        try {
          const deleteResponseB = await agentBay.delete(sessionB);
          log(
            `Delete Session B RequestId: ${
              deleteResponseB.requestId || "undefined"
            }`
          );
        } catch (error) {
          log(`Warning: Error deleting session B: ${error}`);
        }
      }
    });

    it("should list sessions by labels with requestId", async () => {

      // Test 2: List sessions by environment=development label using new API
      const devSessionsResponse = {
        statusCode: 200,
        body: {
          data: [mockSessionAData],
          maxResults: 5,
          totalCount: 1,
          requestId: "mock-request-id-list-dev",
        },
      };

      listSessionStub.resolves(devSessionsResponse);

      const devSessionsParams: ListSessionParams = {
        labels: { environment: "development" },
        maxResults: 5,
      };
      const devSessions = await agentBay.listByLabels(devSessionsParams);
      log(
        `List Sessions by environment=development RequestId: ${
          devSessions.requestId || "undefined"
        }`
      );
      log(
        `Total count: ${devSessions.totalCount}, Max results: ${devSessions.maxResults}`
      );

      // Verify that the response contains requestId
      expect(devSessions.requestId).toBeDefined();
      expect(typeof devSessions.requestId).toBe("string");
      expect(devSessions.requestId).toBe("mock-request-id-list-dev");

      // Verify that session A is in the results
      expect(devSessions.sessionIds.length).toBe(1);
      expect(devSessions.sessionIds[0]).toBe(mockSessionAData.sessionId);

      // Verify API call parameters
      expect(listSessionStub.calledOnce).toBe(true);
      const listCallArgs = listSessionStub.getCall(0).args[0];
      expect(listCallArgs.authorization).toBe("Bearer test-api-key");
      expect(JSON.parse(listCallArgs.labels)).toEqual({
        environment: "development",
      });
      expect(listCallArgs.maxResults).toBe(5);

      // Test 3: List sessions by owner=team-b label
      const teamBSessionsResponse = {
        statusCode: 200,
        body: {
          data: [mockSessionBData],
          requestId: "mock-request-id-list-team-b",
          maxResults: 5,
          totalCount: 1,
        },
      };

      listSessionStub.reset();
      listSessionStub.resolves(teamBSessionsResponse);

      const teamBSessionsParams: ListSessionParams = {
        labels: { owner: "team-b" },
        maxResults: 5,
      };
      const teamBSessions = await agentBay.listByLabels(teamBSessionsParams);
      log(
        `List Sessions by owner=team-b RequestId: ${
          teamBSessions.requestId || "undefined"
        }`
      );
      log(
        `Total count: ${teamBSessions.totalCount}, Max results: ${teamBSessions.maxResults}`
      );

      // Verify that the response contains requestId
      expect(teamBSessions.requestId).toBeDefined();
      expect(teamBSessions.requestId).toBe("mock-request-id-list-team-b");

      // Verify that session B is in the results
      expect(teamBSessions.sessionIds.length).toBe(1);
      expect(teamBSessions.sessionIds[0]).toBe(mockSessionBData.sessionId);

      // Test 4: List sessions with multiple labels
      const multiLabelSessionsResponse = {
        statusCode: 200,
        body: {
          data: [mockSessionBData],
          requestId: "mock-request-id-list-multi",
          maxResults: 5,
          totalCount: 1,
          nextToken: "mock-next-token",
        },
      };

      listSessionStub.reset();
      listSessionStub.resolves(multiLabelSessionsResponse);

      const multiLabelSessionsParams: ListSessionParams = {
        labels: {
          environment: "testing",
          project: "project-y",
        },
        maxResults: 5,
      };
      const multiLabelSessions = await agentBay.listByLabels(
        multiLabelSessionsParams
      );
      log(
        `Found ${multiLabelSessions.sessionIds.length} sessions with environment=testing AND project=project-y`
      );
      log(
        `List Sessions by multiple labels RequestId: ${
          multiLabelSessions.requestId || "undefined"
        }`
      );
      log(
        `Total count: ${multiLabelSessions.totalCount}, Max results: ${multiLabelSessions.maxResults}`
      );

      // Verify that the response contains requestId
      expect(multiLabelSessions.requestId).toBeDefined();
      expect(multiLabelSessions.requestId).toBe("mock-request-id-list-multi");

      // Verify that only session B is in the results
      expect(multiLabelSessions.sessionIds.length).toBe(1);
      expect(multiLabelSessions.sessionIds[0]).toBe(
        mockSessionBData.sessionId
      );

      // Test pagination if there's a next token
      if (multiLabelSessions.nextToken) {
        log("\nTesting pagination with nextToken...");

        const nextPageResponse = {
          statusCode: 200,
          body: {
            data: [mockSessionAData],
            requestId: "mock-request-id-list-next-page",
            maxResults: 5,
            totalCount: 1,
          },
        };

        listSessionStub.reset();
        listSessionStub.resolves(nextPageResponse);

        const nextPageParams: ListSessionParams = {
          ...multiLabelSessionsParams,
          nextToken: multiLabelSessions.nextToken,
        };
        const nextPageSessions = await agentBay.listByLabels(nextPageParams);
        log(`Next page sessions count: ${nextPageSessions.sessionIds.length}`);
        log(`Next page RequestId: ${nextPageSessions.requestId}`);

        // Verify next page response
        expect(nextPageSessions.requestId).toBeDefined();
        expect(nextPageSessions.requestId).toBe(
          "mock-request-id-list-next-page"
        );
        expect(nextPageSessions.sessionIds.length).toBe(1);
        expect(nextPageSessions.sessionIds[0]).toBe(
          mockSessionAData.sessionId
        );

        // Verify API call parameters for next page
        const nextPageCallArgs = listSessionStub.getCall(0).args[0];
        expect(nextPageCallArgs.authorization).toBe("Bearer test-api-key");
        expect(JSON.parse(nextPageCallArgs.labels)).toEqual({
          environment: "testing",
          project: "project-y",
        });
        expect(nextPageCallArgs.maxResults).toBe(5);
        expect(nextPageCallArgs.nextToken).toBe("mock-next-token");
      }

      // Test 5: List sessions with non-existent label
      const nonExistentSessionsResponse = {
        statusCode: 200,
        body: {
          data: [],
          requestId: "mock-request-id-list-empty",
          maxResults: 5,
          totalCount: 0,
        },
      };

      listSessionStub.reset();
      listSessionStub.resolves(nonExistentSessionsResponse);

      const nonExistentSessionsParams: ListSessionParams = {
        labels: { "non-existent": "value" },
        maxResults: 5,
      };
      const nonExistentSessions = await agentBay.listByLabels(
        nonExistentSessionsParams
      );
      log(
        `Found ${nonExistentSessions.sessionIds.length} sessions with non-existent label`
      );
      log(
        `List Sessions by non-existent label RequestId: ${
          nonExistentSessions.requestId || "undefined"
        }`
      );
      log(
        `Total count: ${nonExistentSessions.totalCount}, Max results: ${nonExistentSessions.maxResults}`
      );

      // Verify that the response contains requestId even for empty results
      expect(nonExistentSessions.requestId).toBeDefined();
      expect(nonExistentSessions.requestId).toBe("mock-request-id-list-empty");

      // Verify empty results
      expect(nonExistentSessions.sessionIds.length).toBe(0);

      // Verify API calls were made with correct parameters
      expect(listSessionStub.called).toBe(true);

      log("Test completed successfully");
    });
  });

  describe("list", () => {
    let agentBay: AgentBay;

    beforeEach(() => {
      const apiKey = "test-api-key";
      agentBay = new AgentBay({ apiKey });
    });

    it("should list all sessions without labels", async () => {
      const mockResponse = {
        statusCode: 200,
        body: {
          success: true,
          data: [mockSessionAData, mockSessionBData, mockSessionData],
          maxResults: 10,
          totalCount: 3,
          requestId: "mock-request-id-list-all",
        },
      };

      listSessionStub.resolves(mockResponse);

      const result = await agentBay.list();

      expect(result.success).toBe(true);
      expect(result.requestId).toBe("mock-request-id-list-all");
      expect(result.sessionIds.length).toBe(3);
      expect(result.totalCount).toBe(3);
    });

    it("should list sessions with specific labels", async () => {
      const mockResponse = {
        statusCode: 200,
        body: {
          success: true,
          data: [mockSessionAData],
          maxResults: 10,
          totalCount: 1,
          requestId: "mock-request-id-list-labeled",
        },
      };

      listSessionStub.resolves(mockResponse);

      const result = await agentBay.list({ env: "prod" });

      expect(result.success).toBe(true);
      expect(result.requestId).toBe("mock-request-id-list-labeled");
      expect(result.sessionIds.length).toBe(1);
      expect(listSessionStub.calledOnce).toBe(true);
      const callArgs = listSessionStub.getCall(0).args[0];
      expect(JSON.parse(callArgs.labels)).toEqual({ env: "prod" });
    });

    it("should list sessions with pagination", async () => {
      // First page response
      const mockResponsePage1 = {
        statusCode: 200,
        body: {
          success: true,
          data: [mockSessionAData, mockSessionBData],
          maxResults: 2,
          totalCount: 4,
          nextToken: "token-page2",
          requestId: "mock-request-id-page1",
        },
      };

      // Second page response
      const mockResponsePage2 = {
        statusCode: 200,
        body: {
          success: true,
          data: [mockSessionData],
          maxResults: 2,
          totalCount: 4,
          nextToken: "",
          requestId: "mock-request-id-page2",
        },
      };

      listSessionStub.onFirstCall().resolves(mockResponsePage1);
      listSessionStub.onSecondCall().resolves(mockResponsePage2);

      // Request page 2
      const result = await agentBay.list({ env: "prod" }, 2, 2);

      expect(result.success).toBe(true);
      expect(result.requestId).toBe("mock-request-id-page2");
      expect(result.sessionIds.length).toBe(1);
      expect(result.sessionIds[0]).toBe(mockSessionData.sessionId);
      expect(listSessionStub.calledTwice).toBe(true);
    });

    it("should use default limit of 10 when not specified", async () => {
      const mockResponse = {
        statusCode: 200,
        body: {
          success: true,
          data: [mockSessionAData],
          maxResults: 10,
          totalCount: 1,
          requestId: "mock-request-id",
        },
      };

      listSessionStub.resolves(mockResponse);

      await agentBay.list();

      const callArgs = listSessionStub.getCall(0).args[0];
      expect(callArgs.maxResults).toBe(10);
    });
  });

  describe("policyId passthrough", () => {
    it("should pass policyId to CreateMcpSession request body", async () => {
      const apiKey = "test-api-key";
      const agentBay = new AgentBay({ apiKey });

      const createMockResponse = {
        statusCode: 200,
        body: {
          data: mockSessionData,
          requestId: "mock-request-id-create",
        },
      };
      createMcpSessionStub.resolves(createMockResponse);

      const policyId = "policy-xyz";
      await agentBay.create({ policyId });

      expect(createMcpSessionStub.calledOnce).toBe(true);
      const createCallArgs = createMcpSessionStub.getCall(0).args[0];
      expect(createCallArgs.mcpPolicyId).toBe(policyId);
    });
  });
});
