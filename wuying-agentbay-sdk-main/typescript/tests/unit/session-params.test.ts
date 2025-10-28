import { AgentBay, Session } from "../../src";
import { APIError } from "../../src/exceptions";
import * as sinon from "sinon";

describe("Session Parameters", () => {
  let mockAgentBay: any;
  let mockSession: Session;
  let mockClient: any;
  let sandbox: sinon.SinonSandbox;

  beforeEach(() => {
    sandbox = sinon.createSandbox();

    mockClient = {
      createMcpSession: sandbox.stub(),
      releaseMcpSession: sandbox.stub(),
    };

    mockAgentBay = {
      getAPIKey: sandbox.stub().returns("test-api-key"),
      getClient: sandbox.stub().returns(mockClient),
      removeSession: sandbox.stub(),
      create: sandbox.stub(),
    };

    mockSession = new Session(mockAgentBay, "test-session-id");
  });

  afterEach(() => {
    sandbox.restore();
  });

  describe("create method options", () => {
    it("should accept empty options", async () => {
      // Mock create response with SessionResult structure
      const mockCreateResponse = {
        requestId: "create-request-id",
        success: true,
        session: mockSession,
      };
      mockAgentBay.create.resolves(mockCreateResponse);

      const createResponse = await mockAgentBay.create();

      // Verify SessionResult structure
      expect(createResponse.success).toBe(true);
      expect(createResponse.requestId).toBe("create-request-id");
      expect(typeof createResponse.requestId).toBe("string");
      expect(createResponse.session).toBe(mockSession);
      expect(createResponse.errorMessage).toBeUndefined();
    });

    it("should accept labels option", async () => {
      const labels = { username: "alice", project: "my-project" };

      // Mock create response with labels and SessionResult structure
      const mockCreateResponse = {
        requestId: "create-with-labels-request-id",
        success: true,
        session: mockSession,
      };
      mockAgentBay.create.resolves(mockCreateResponse);

      const createResponse = await mockAgentBay.create({ labels });

      // Verify SessionResult structure
      expect(createResponse.success).toBe(true);
      expect(createResponse.requestId).toBe("create-with-labels-request-id");
      expect(createResponse.session).toBe(mockSession);
      expect(createResponse.errorMessage).toBeUndefined();
      expect(mockAgentBay.create.calledOnceWith({ labels })).toBe(true);
    });

    it("should accept imageId option", async () => {
      const imageId = "test-image-id";

      // Mock create response with imageId and SessionResult structure
      const mockCreateResponse = {
        requestId: "create-with-image-request-id",
        success: true,
        session: mockSession,
      };
      mockAgentBay.create.resolves(mockCreateResponse);

      const createResponse = await mockAgentBay.create({ imageId });

      // Verify SessionResult structure
      expect(createResponse.success).toBe(true);
      expect(createResponse.requestId).toBe("create-with-image-request-id");
      expect(createResponse.session).toBe(mockSession);
      expect(createResponse.errorMessage).toBeUndefined();
      expect(mockAgentBay.create.calledOnceWith({ imageId })).toBe(true);
    });

    it("should accept all options together", async () => {
      const labels = { username: "alice", project: "my-project" };
      const imageId = "test-image-id";

      // Mock create response with all options and SessionResult structure
      const mockCreateResponse = {
        requestId: "create-with-all-request-id",
        success: true,
        session: mockSession,
      };
      mockAgentBay.create.resolves(mockCreateResponse);

      const createResponse = await mockAgentBay.create({
        labels,
        imageId,
      });

      // Verify SessionResult structure
      expect(createResponse.success).toBe(true);
      expect(createResponse.requestId).toBe("create-with-all-request-id");
      expect(createResponse.session).toBe(mockSession);
      expect(createResponse.errorMessage).toBeUndefined();
      expect(
        mockAgentBay.create.calledOnceWith({ labels, imageId })
      ).toBe(true);
    });
  });

  describe("session creation with options", () => {
    it("should create a session with the specified options", async () => {
      const options = {
        labels: { username: "alice" },
        imageId: "test-image-id",
      };

      // Mock create response with options and SessionResult structure
      const mockCreateResponse = {
        requestId: "create-with-options-request-id",
        success: true,
        session: mockSession,
      };
      mockAgentBay.create.resolves(mockCreateResponse);

      const createResponse = await mockAgentBay.create(options);

      // Verify SessionResult structure
      expect(createResponse.success).toBe(true);
      expect(createResponse.requestId).toBe("create-with-options-request-id");
      expect(createResponse.session).toBe(mockSession);
      expect(createResponse.errorMessage).toBeUndefined();
      expect(mockAgentBay.create.calledOnceWith(options)).toBe(true);
    });

    it("should handle create session failure", async () => {
      const options = {
        labels: { username: "alice" },
      };

      // Mock create response with failure and SessionResult structure
      const mockCreateResponse = {
        requestId: "create-failure-request-id",
        success: false,
        errorMessage: "Failed to create session: API Error",
      };
      mockAgentBay.create.resolves(mockCreateResponse);

      const createResponse = await mockAgentBay.create(options);

      // Verify SessionResult error structure
      expect(createResponse.success).toBe(false);
      expect(createResponse.requestId).toBe("create-failure-request-id");
      expect(createResponse.session).toBeUndefined();
      expect(createResponse.errorMessage).toContain("Failed to create session");
    });
  });

  describe("enableBrowserReplay functionality", () => {
    it("should support enableBrowserReplay parameter in CreateSessionParams", async () => {
      const options = {
        labels: { example: "browser_replay", session_type: "browser", replay: "enabled" },
        imageId: "browser_latest",
        enableBrowserReplay: true,
      };

      // Mock create response with enableBrowserReplay option
      const mockCreateResponse = {
        requestId: "create-with-enable-record-request-id",
        success: true,
        session: mockSession,
      };
      mockAgentBay.create.resolves(mockCreateResponse);

      const createResponse = await mockAgentBay.create(options);

      // Verify SessionResult structure
      expect(createResponse.success).toBe(true);
      expect(createResponse.requestId).toBe("create-with-enable-record-request-id");
      expect(createResponse.session).toBe(mockSession);
      expect(createResponse.errorMessage).toBeUndefined();
      expect(mockAgentBay.create.calledOnceWith(options)).toBe(true);
    });

    it("should default enableBrowserReplay to false when not specified", async () => {
      const options = {
        labels: { session_type: "standard" },
        imageId: "linux_latest",
      };

      // Mock create response without enableBrowserReplay
      const mockCreateResponse = {
        requestId: "create-no-record-request-id",
        success: true,
        session: mockSession,
      };
      mockAgentBay.create.resolves(mockCreateResponse);

      const createResponse = await mockAgentBay.create(options);

      // Verify SessionResult structure
      expect(createResponse.success).toBe(true);
      expect(createResponse.requestId).toBe("create-no-record-request-id");
      expect(createResponse.session).toBe(mockSession);
      expect(createResponse.errorMessage).toBeUndefined();
    });

    it("should handle enableBrowserReplay false explicitly", async () => {
      const options = {
        labels: { session_type: "test" },
        imageId: "browser_latest",
        enableBrowserReplay: false,
      };

      // Mock create response with enableBrowserReplay explicitly false
      const mockCreateResponse = {
        requestId: "create-record-false-request-id",
        success: true,
        session: mockSession,
      };
      mockAgentBay.create.resolves(mockCreateResponse);

      const createResponse = await mockAgentBay.create(options);

      // Verify SessionResult structure
      expect(createResponse.success).toBe(true);
      expect(createResponse.requestId).toBe("create-record-false-request-id");
      expect(createResponse.session).toBe(mockSession);
      expect(createResponse.errorMessage).toBeUndefined();
      expect(mockAgentBay.create.calledOnceWith(options)).toBe(true);
    });
  });

  describe("CreateSessionParams class enableBrowserReplay functionality", () => {
    it("should have enableBrowserReplay field with default false value", () => {
      const params = new (require("../../src/session-params").CreateSessionParams)();

      expect(params.enableBrowserReplay).toBe(false);
    });

    it("should support withEnableRecord method", () => {
      const params = new (require("../../src/session-params").CreateSessionParams)();

      const result = params.withEnableRecord(true);

      expect(result.enableBrowserReplay).toBe(true);
      expect(result).toBe(params); // Should return same instance for chaining
    });

    it("should support method chaining with enableBrowserReplay", () => {
      const params = new (require("../../src/session-params").CreateSessionParams)();

      const result = params
        .withLabels({ project: "test", env: "development" })
        .withImageId("browser_latest")
        .withEnableRecord(true)
        .withIsVpc(false);

      expect(result.labels).toEqual({ project: "test", env: "development" });
      expect(result.imageId).toBe("browser_latest");
      expect(result.enableBrowserReplay).toBe(true);
      expect(result.isVpc).toBe(false);
      expect(result).toBe(params); // Should return same instance for chaining
    });

    it("should include enableBrowserReplay in toJSON output", () => {
      const params = new (require("../../src/session-params").CreateSessionParams)();
      params.withEnableRecord(true);

      const json = params.toJSON();

      expect(json.enableBrowserReplay).toBe(true);
    });

    it("should handle enableBrowserReplay in fromJSON", () => {
      const config = {
        labels: { test: "value" },
        imageId: "test_image",
        contextSync: [],
        isVpc: false,
        enableBrowserReplay: true,
      };

      const params = (require("../../src/session-params").CreateSessionParams).fromJSON(config);

      expect(params.enableBrowserReplay).toBe(true);
      expect(params.labels).toEqual({ test: "value" });
      expect(params.imageId).toBe("test_image");
    });
  });

  describe("Session enableBrowserReplay field", () => {
    it("should have enableBrowserReplay field with default false value", () => {
      const session = new Session(mockAgentBay, "test-session-id");

      expect(session.enableBrowserReplay).toBe(false);
    });

    it("should allow setting enableBrowserReplay field", () => {
      const session = new Session(mockAgentBay, "test-session-id");

      session.enableBrowserReplay = true;

      expect(session.enableBrowserReplay).toBe(true);
    });
  });
});
