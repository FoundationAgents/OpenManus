import { AgentBay } from "../../src/agent-bay";
import { newContextSync, SyncPolicy, BWList, WhiteList } from "../../src/context-sync";

describe("WhiteListValidationIntegration", () => {
  let agentBay: AgentBay;
  let contextId: string;

  const apiKey = process.env.AGENTBAY_API_KEY;
  const shouldSkip = !apiKey || process.env.CI;

  beforeAll(async () => {
    if (shouldSkip) {
      return;
    }

    agentBay = new AgentBay({ apiKey: apiKey! });

    const contextName = `test-wildcard-validation-${Date.now()}`;
    const contextResult = await agentBay.context.get(contextName, true);
    
    if (!contextResult.success || !contextResult.context) {
      throw new Error("Failed to create context");
    }
    
    contextId = contextResult.context.id;
  });

  afterAll(async () => {
    if (shouldSkip || !agentBay || !contextId) {
      return;
    }

    const contextResult = await agentBay.context.get(`test-wildcard-validation-${contextId}`, false);
    if (contextResult.success && contextResult.context) {
      await agentBay.context.delete(contextResult.context);
    }
  });

  it("should fail when creating session with wildcard in path", async () => {
    if (shouldSkip) {
      return;
    }
    const policy: SyncPolicy = {
      bwList: {
        whiteLists: [{ path: "*.json" }]
      }
    };

    expect(() => {
      newContextSync(contextId, "/tmp/data", policy);
    }).toThrow("Wildcard patterns are not supported in path");
    
    expect(() => {
      newContextSync(contextId, "/tmp/data", policy);
    }).toThrow("*.json");
  });

  it("should fail when creating session with wildcard in exclude_paths", async () => {
    if (shouldSkip) {
      return;
    }
    const policy: SyncPolicy = {
      bwList: {
        whiteLists: [{ path: "/src", excludePaths: ["*.log"] }]
      }
    };

    expect(() => {
      newContextSync(contextId, "/tmp/data", policy);
    }).toThrow("Wildcard patterns are not supported in exclude_paths");
    
    expect(() => {
      newContextSync(contextId, "/tmp/data", policy);
    }).toThrow("*.log");
  });

  it("should fail when creating session with glob pattern", async () => {
    if (shouldSkip) {
      return;
    }
    const policy: SyncPolicy = {
      bwList: {
        whiteLists: [{ path: "/data/*" }]
      }
    };

    expect(() => {
      newContextSync(contextId, "/tmp/data", policy);
    }).toThrow("Wildcard patterns are not supported in path");
    
    expect(() => {
      newContextSync(contextId, "/tmp/data", policy);
    }).toThrow("/data/*");
  });

  it("should fail when creating session with double asterisk", async () => {
    if (shouldSkip) {
      return;
    }
    const policy: SyncPolicy = {
      bwList: {
        whiteLists: [{ path: "/logs/**/*.txt" }]
      }
    };

    expect(() => {
      newContextSync(contextId, "/tmp/data", policy);
    }).toThrow("Wildcard patterns are not supported in path");
  });

  it("should succeed when creating session with valid paths", async () => {
    if (shouldSkip) {
      return;
    }
    const policy: SyncPolicy = {
      bwList: {
        whiteLists: [
          { path: "/src", excludePaths: ["/node_modules", "/temp"] }
        ]
      }
    };

    const contextSync = newContextSync(contextId, "/tmp/data", policy);
    
    const sessionResult = await agentBay.create({
      contextSync: [contextSync],
      imageId: "linux_latest"
    });

    expect(sessionResult.success).toBe(true);
    expect(sessionResult.session).toBeDefined();

    if (sessionResult.session) {
      await agentBay.delete(sessionResult.session);
    }
  });

  it("should validate before API call", () => {
    if (shouldSkip) {
      return;
    }
    const policy: SyncPolicy = {
      bwList: {
        whiteLists: [{ path: "*.txt" }]
      }
    };

    expect(() => {
      newContextSync(contextId, "/tmp/data", policy);
    }).toThrow("Wildcard patterns are not supported in path");
  });
});
