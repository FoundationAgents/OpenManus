import { Session } from "../session";
import {
  CommandResult,
} from "../types/api-response";


/**
 * Handles command execution operations in the AgentBay cloud environment.
 */
export class Command {
  private session: Session;

  /**
   * Initialize a Command object.
   *
   * @param session - The Session instance that this Command belongs to.
   */
  constructor(session: Session) {
    this.session = session;
  }

  /**
   * Sanitizes error messages to remove sensitive information like API keys.
   *
   * @param error - The error to sanitize
   * @returns The sanitized error
   */
  private sanitizeError(error: any): any {
    if (!error) {
      return error;
    }

    const errorString = String(error);
    return errorString.replace(/Bearer\s+[^\s]+/g, "Bearer [REDACTED]");
  }

  /**
   * Execute a command in the session environment.
   * Corresponds to Python's execute_command() method
   *
   * @param command - The command to execute
   * @param timeoutMs - The timeout in milliseconds. Default is 1000ms.
   * @returns CommandResult with command output and requestId
   * @throws APIError if the operation fails.
   */
  async executeCommand(
    command: string,
    timeoutMs = 1000
  ): Promise<CommandResult> {
    try {
      const args = {
        command,
        timeout_ms: timeoutMs,
      };
      const result = await this.session.callMcpTool("shell", args);

      return {
        requestId: result.requestId,
        success: result.success,
        output: result.data,
        errorMessage: result.errorMessage,
      };
    } catch (error) {
      return {
        requestId: "",
        success: false,
        output: "",
        errorMessage: `Failed to execute command: ${error}`,
      };
    }
  }
}
