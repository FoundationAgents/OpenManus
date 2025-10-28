import { expect } from "chai";
import * as sinon from "sinon";
import { Code } from "../../src/code/code";
import { APIError } from "../../src/exceptions";

describe("Code", () => {
  let code: Code;
  let mockSession: any;
  let callMcpToolStub: sinon.SinonStub;

  beforeEach(() => {
    // Create mock session
    mockSession = {
      getAPIKey: sinon.stub().returns("test-api-key"),
      getSessionId: sinon.stub().returns("test-session-id"),
      callMcpTool: sinon.stub(),
    };

    code = new Code(mockSession);
    
    // Get reference to the callMcpTool stub
    callMcpToolStub = mockSession.callMcpTool;
  });

  afterEach(() => {
    sinon.restore();
  });

  describe("runCode", () => {
    it("should execute Python code successfully", async () => {
      // Setup mock response - new format
      const mockResult = {
        success: true,
        data: "Hello, world!\\n2\\n",
        errorMessage: "",
        requestId: "test-request-id",
      };
      callMcpToolStub.resolves(mockResult);

      const pythonCode = `
print("Hello, world!")
x = 1 + 1
print(x)
`;

      // Execute the test
      const result = await code.runCode(pythonCode, "python");

      // Verify results
      expect(result.success).to.be.true;
      expect(result.requestId).to.equal("test-request-id");
      expect(result.result).to.equal("Hello, world!\\n2\\n");
      expect(result.errorMessage).to.be.undefined;

      // Verify method was called correctly
      expect(callMcpToolStub.calledOnceWith(
        "run_code",
        {
          code: pythonCode,
          language: "python",
          timeout_s: 60,
        }
      )).to.be.true;
    });

    it("should execute JavaScript code with custom timeout", async () => {
      // Setup mock response - new format
      const mockResult = {
        success: true,
        data: "Hello, world!\\n2\\n",
        errorMessage: "",
        requestId: "test-request-id",
      };
      callMcpToolStub.resolves(mockResult);

      const jsCode = `
console.log("Hello, world!");
const x = 1 + 1;
console.log(x);
`;
      const customTimeout = 600;

      // Execute the test
      const result = await code.runCode(jsCode, "javascript", customTimeout);

      // Verify results
      expect(result.success).to.be.true;
      expect(result.requestId).to.equal("test-request-id");
      expect(result.result).to.equal("Hello, world!\\n2\\n");
      expect(result.errorMessage).to.be.undefined;

      // Verify method was called with custom timeout
      expect(callMcpToolStub.calledOnceWith(
        "run_code",
        {
          code: jsCode,
          language: "javascript",
          timeout_s: customTimeout,
        }
      )).to.be.true;
    });

    it("should handle unsupported language", async () => {
      // Execute the test with unsupported language
      const result = await code.runCode("print('test')", "ruby");

      // Verify error handling
      expect(result.success).to.be.false;
      expect(result.result).to.equal("");
      expect(result.errorMessage).to.equal(
        "Unsupported language: ruby. Supported languages are 'python' and 'javascript'"
      );

      // Verify callMcpTool was not called for unsupported language
      expect(callMcpToolStub.called).to.be.false;
    });

    it("should handle code execution failure", async () => {
      // Setup mock error
      callMcpToolStub.rejects(new APIError("Code execution failed"));

      // Execute the test
      const result = await code.runCode("print('test')", "python");

      // Verify error handling
      expect(result.success).to.be.false;
      expect(result.result).to.equal("");
      expect(result.errorMessage).to.contain("Code execution failed");
    });

    it("should handle empty code input", async () => {
      // Setup mock response - new format
      const mockResult = {
        success: true,
        data: "",
        errorMessage: "",
        requestId: "test-request-id",
      };
      callMcpToolStub.resolves(mockResult);

      // Execute the test
      const result = await code.runCode("", "python");

      // Verify results
      expect(result.success).to.be.true;
      expect(result.requestId).to.equal("test-request-id");
      expect(result.result).to.equal("");
      expect(result.errorMessage).to.be.undefined;
    });
  });
}); 