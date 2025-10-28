import {
  CodeExecutionResult,
} from "../types/api-response";

/**
 * Handles code execution operations in the AgentBay cloud environment.
 */
export class Code {
  private session: {
    getAPIKey(): string;
    getSessionId(): string;
    callMcpTool(toolName: string, args: any): Promise<{
      success: boolean;
      data: string;
      errorMessage: string;
      requestId: string;
    }>;
  };

  /**
   * Initialize a Code object.
   *
   * @param session - The Session instance that this Code belongs to.
   */
  constructor(session: {
    getAPIKey(): string;
    getSessionId(): string;
    callMcpTool(toolName: string, args: any): Promise<{
      success: boolean;
      data: string;
      errorMessage: string;
      requestId: string;
    }>;
  }) {
    this.session = session;
  }

  /**
   * Execute code in the specified language with a timeout.
   * Corresponds to Python's run_code() method
   *
   * @param code - The code to execute.
   * @param language - The programming language of the code. Must be either 'python' or 'javascript'.
   * @param timeoutS - The timeout for the code execution in seconds. Default is 60s.
   *                   Note: Due to gateway limitations, each request cannot exceed 60 seconds.
   * @returns CodeExecutionResult with code execution output and requestId
   * @throws Error if an unsupported language is specified.
   */
  async runCode(
    code: string,
    language: string,
    timeoutS = 60
  ): Promise<CodeExecutionResult> {
    try {
      // Validate language
      if (language !== "python" && language !== "javascript") {
        return {
          requestId: "",
          success: false,
          result: "",
          errorMessage: `Unsupported language: ${language}. Supported languages are 'python' and 'javascript'`,
        };
      }

      const args = {
        code,
        language,
        timeout_s: timeoutS,
      };

      const response = await this.session.callMcpTool(
        "run_code",
        args
      );

      if (!response.success) {
        return {
          requestId: response.requestId,
          success: false,
          result: "",
          errorMessage: response.errorMessage,
        };
      }

      return {
        requestId: response.requestId,
        success: true,
        result: response.data || "",
      };
    } catch (error) {
      return {
        requestId: "",
        success: false,
        result: "",
        errorMessage: `Failed to run code: ${error}`,
      };
    }
  }
} 