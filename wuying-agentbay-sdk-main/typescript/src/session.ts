import { AgentBay } from "./agent-bay";
import { Agent } from "./agent/agent";
import { Client } from "./api/client";
import {
  CallMcpToolRequest,
  GetLabelRequest,
  GetLinkRequest,
  GetMcpResourceRequest,
  ListMcpToolsRequest,
  ReleaseMcpSessionRequest,
  SetLabelRequest,
} from "./api/models/model";
import { Application } from "./application";
import { Browser } from "./browser";
import { Code } from "./code";
import { Command } from "./command";
import { Computer } from "./computer";
import { ContextManager, newContextManager } from "./context-manager";
import { FileSystem } from "./filesystem";
import { Mobile } from "./mobile";
import { Oss } from "./oss";
import {
  DeleteResult,
  extractRequestId,
  OperationResult,
} from "./types/api-response";
import { UI } from "./ui";
import { log, logError } from "./utils/logger";
import { WindowManager } from "./window";

/**
 * Represents an MCP tool with complete information.
 */
export interface McpTool {
  name: string;
  description: string;
  inputSchema: Record<string, any>;
  server: string;
  tool: string;
}

/**
 * Result containing MCP tools list and request ID.
 */
export interface McpToolsResult extends OperationResult {
  tools: McpTool[];
}

/**
 * Result containing MCP resource information and request ID.
 */
export interface McpResourceResult extends OperationResult {
  uri: string;
  name: string;
  description: string;
  mimeType: string;
}

/**
 * Result containing MCP resource content and request ID.
 */
export interface McpResourceContentResult extends OperationResult {
  contents: Array<{
    uri: string;
    mimeType: string;
    text?: string;
    blob?: string;
  }>;
}

/**
 * Contains information about a session.
 */
export interface SessionInfo {
  sessionId: string;
  resourceUrl: string;
  appId?: string;
  authCode?: string;
  connectionProperties?: string;
  resourceId?: string;
  resourceType?: string;
  ticket?: string;
}

/**
 * SessionInfo class to match Python version structure
 */
export class SessionInfoClass {
  sessionId: string;
  resourceUrl: string;
  appId: string;
  authCode: string;
  connectionProperties: string;
  resourceId: string;
  resourceType: string;
  ticket: string;

  constructor(
    sessionId = "",
    resourceUrl = "",
    appId = "",
    authCode = "",
    connectionProperties = "",
    resourceId = "",
    resourceType = "",
    ticket = ""
  ) {
    this.sessionId = sessionId;
    this.resourceUrl = resourceUrl;
    this.appId = appId;
    this.authCode = authCode;
    this.connectionProperties = connectionProperties;
    this.resourceId = resourceId;
    this.resourceType = resourceType;
    this.ticket = ticket;
  }
}

/**
 * Represents a session in the AgentBay cloud environment.
 */
export class Session {
  private agentBay: AgentBay;
  public sessionId: string;

  // File transfer context ID
  public fileTransferContextId: string | null = null;

  // VPC-related information
  public isVpc = false; // Whether this session uses VPC resources
  public networkInterfaceIp = ""; // Network interface IP for VPC sessions
  public httpPort = ""; // HTTP port for VPC sessions
  public token = ""; // Token for VPC sessions

  // Resource URL for accessing the session
  public resourceUrl = "";

  // Recording functionality
  public enableBrowserReplay = false; // Whether browser recording is enabled for this session

  // File, command, code, and oss handlers (matching Python naming)
  public fileSystem: FileSystem; // file_system in Python
  public command: Command;
  public code: Code;
  public oss: Oss;

  // Application, window, and UI management (matching Python naming)
  public application: Application; // application in Python (ApplicationManager)
  public window: WindowManager;
  public ui: UI;

  // Computer and Mobile automation (new modules)
  public computer: Computer;
  public mobile: Mobile;

  // Agent for task execution
  public agent: Agent;

  // Browser for web automation
  public browser: Browser;

  // Context management (matching Go version)
  public context: ContextManager;

  // MCP tools available for this session
  public mcpTools: McpTool[] = [];

  /**
   * Initialize a Session object.
   *
   * @param agentBay - The AgentBay instance that created this session.
   * @param sessionId - The ID of this session.
   */
  constructor(agentBay: AgentBay, sessionId: string) {
    this.agentBay = agentBay;
    this.sessionId = sessionId;

    // Initialize file system, command and code handlers (matching Python naming)
    this.fileSystem = new FileSystem(this);
    this.command = new Command(this);
    this.code = new Code(this);
    this.oss = new Oss(this);

    // Initialize application and window managers (matching Python naming)
    this.application = new Application(this);
    this.window = new WindowManager(this);
    this.ui = new UI(this);

    // Initialize Computer and Mobile modules
    this.computer = new Computer(this);
    this.mobile = new Mobile(this);

    // Initialize Agent
    this.agent = new Agent(this);

    // Initialize Browser
    this.browser = new Browser(this);

    // Initialize context manager (matching Go version)
    this.context = newContextManager(this);
  }

  /**
   * Return the AgentBay instance that created this session.
   */
  getAgentBay(): AgentBay {
    return this.agentBay;
  }

  /**
   * Return the API key for this session.
   */
  getAPIKey(): string {
    return this.agentBay.getAPIKey();
  }

  /**
   * Return the HTTP client for this session.
   */
  getClient(): Client {
    return this.agentBay.getClient();
  }

  /**
   * Return the session_id for this session.
   */
  getSessionId(): string {
    return this.sessionId;
  }

  /**
   * Return whether this session uses VPC resources.
   */
  isVpcEnabled(): boolean {
    return this.isVpc;
  }

  /**
   * Return the network interface IP for VPC sessions.
   */
  getNetworkInterfaceIp(): string {
    return this.networkInterfaceIp;
  }

  /**
   * Return the HTTP port for VPC sessions.
   */
  getHttpPort(): string {
    return this.httpPort;
  }

  /**
   * Return the token for VPC sessions.
   */
  getToken(): string {
    return this.token;
  }

  /**
   * Find the server that provides the given tool.
   */
  findServerForTool(toolName: string): string {
    for (const tool of this.mcpTools) {
      if (tool.name === toolName) {
        return tool.server;
      }
    }
    return "";
  }

  /**
   * Delete this session.
   *
   * @param syncContext - Whether to sync context data (trigger file uploads) before deleting the session. Defaults to false.
   * @returns DeleteResult indicating success or failure and request ID
   */
  async delete(syncContext = false): Promise<DeleteResult> {
    try {
      // If syncContext is true, trigger file uploads first
      if (syncContext) {
        log("Triggering context synchronization before session deletion...");

        // Use the new sync method without callback (sync mode)
        const syncStartTime = Date.now();

        try {
          const syncResult = await this.context.sync();

          const syncDuration = Date.now() - syncStartTime;

          if (syncResult.success) {
            log(`Context sync completed in ${syncDuration}ms`);
          } else {
            log(`Context sync completed with failures after ${syncDuration}ms`);
          }
        } catch (error) {
          const syncDuration = Date.now() - syncStartTime;
          logError(`Failed to trigger context sync after ${syncDuration}ms:`, error);
          // Continue with deletion even if sync fails
        }
      }

      // Proceed with session deletion
      const request = new ReleaseMcpSessionRequest({
        authorization: `Bearer ${this.getAPIKey()}`,
        sessionId: this.sessionId,
      });

      const response = await this.getClient().releaseMcpSession(request);
      log(`Response from release_mcp_session: ${JSON.stringify(response)}`);

      // Extract request ID
      const requestId = extractRequestId(response) || "";

      // Check if the response is success (matching Python logic)
      const responseBody = response.body;
      const success = responseBody?.success !== false; // Note: capital S to match Python

      if (!success) {
        const errorMessage = `[${responseBody?.code || 'Unknown'}] ${responseBody?.message || 'Failed to delete session'}`;
        return {
          requestId,
          success: false,
          errorMessage,
        };
      }

      // Return success result with request ID
      return {
        requestId,
        success: true,
      };
    } catch (error) {
      logError("Error calling release_mcp_session:", error);
      // In case of error, return failure result with error message (matching Python)
      return {
        requestId: "",
        success: false,
        errorMessage: `Failed to delete session ${this.sessionId}: ${error}`,
      };
    }
  }

  /**
   * Validates labels parameter for label operations.
   *
   * @param labels - The labels to validate
   * @returns null if validation passes, or OperationResult with error if validation fails
   */
  private validateLabels(labels: Record<string, string>): OperationResult | null {
    // Check if labels is null, undefined, or invalid type
    if (!labels || typeof labels !== 'object') {
      return {
        requestId: "",
        success: false,
        errorMessage: "Labels cannot be null, undefined, or invalid type. Please provide a valid labels object.",
      };
    }

    // Check if labels is an array or other non-plain object
    if (Array.isArray(labels)) {
      return {
        requestId: "",
        success: false,
        errorMessage: "Labels cannot be an array. Please provide a valid labels object.",
      };
    }

    // Check if labels is a Date, RegExp, or other built-in object types
    if (labels instanceof Date || labels instanceof RegExp || labels instanceof Error ||
        labels instanceof Map || labels instanceof Set || labels instanceof WeakMap ||
        labels instanceof WeakSet || labels instanceof Promise) {
      return {
        requestId: "",
        success: false,
        errorMessage: "Labels must be a plain object. Built-in object types are not allowed.",
      };
    }

    // Check if labels object is empty
    if (Object.keys(labels).length === 0) {
      return {
        requestId: "",
        success: false,
        errorMessage: "Labels cannot be empty. Please provide at least one label.",
      };
    }

    for (const [key, value] of Object.entries(labels)) {
      // Check key validity
      if (!key || key.trim() === "") {
        return {
          requestId: "",
          success: false,
          errorMessage: "Label keys cannot be empty Please provide valid keys.",
        };
      }

      // Check value is not null or undefined
      if (!value || value.trim() === "") {
        return {
          requestId: "",
          success: false,
          errorMessage: "Label values cannot be empty Please provide valid values.",
        };
      }
    }

    // Validation passed
    return null;
  }

  /**
   * Sets the labels for this session.
   *
   * @param labels - The labels to set for the session.
   * @returns OperationResult indicating success or failure with request ID
   * @throws Error if the operation fails (matching Python SessionError)
   */
  async setLabels(labels: Record<string, string>): Promise<OperationResult> {
    try {
      // Validate labels using the extracted validation function
      const validationResult = this.validateLabels(labels);
      if (validationResult !== null) {
        return validationResult;
      }

      // Convert labels to JSON string
      const labelsJSON = JSON.stringify(labels);

      const request = new SetLabelRequest({
        authorization: `Bearer ${this.getAPIKey()}`,
        sessionId: this.sessionId,
        labels: labelsJSON,
      });

      const response = await this.getClient().setLabel(request);

      // Extract request ID
      const requestId = extractRequestId(response) || "";

      return {
        requestId,
        success: true,
      };
    } catch (error) {
      logError("Error calling set_label:", error);
      throw new Error(
        `Failed to set labels for session ${this.sessionId}: ${error}`
      );
    }
  }

  /**
   * Gets the labels for this session.
   *
   * @returns OperationResult containing the labels as data and request ID
   * @throws Error if the operation fails (matching Python SessionError)
   */
  async getLabels(): Promise<OperationResult> {
    try {
      const request = new GetLabelRequest({
        authorization: `Bearer ${this.getAPIKey()}`,
        sessionId: this.sessionId,
      });

      const response = await this.getClient().getLabel(request);

      // Extract request ID
      const requestId = extractRequestId(response) || "";

      // Extract labels from response (matching Python structure)
      const responseBody = response?.body;
      const data = responseBody?.data; // Capital D to match Python
      const labelsJSON = data?.labels; // Capital L to match Python

      let labels = {};
      if (labelsJSON) {
        labels = JSON.parse(labelsJSON);
      }

      return {
        requestId,
        success: true,
        data: labels,
      };
    } catch (error) {
      logError("Error calling get_label:", error);
      throw new Error(
        `Failed to get labels for session ${this.sessionId}: ${error}`
      );
    }
  }

  /**
   * Gets information about this session.
   *
   * @returns OperationResult containing the session information as data and request ID
   * @throws Error if the operation fails (matching Python SessionError)
   */
  async info(): Promise<OperationResult> {
    try {
      const request = new GetMcpResourceRequest({
        authorization: `Bearer ${this.getAPIKey()}`,
        sessionId: this.sessionId,
      });

      log("API Call: GetMcpResource");
      log(`Request: SessionId=${this.sessionId}`);

      const response = await this.getClient().getMcpResource(request);
      log(`Response from GetMcpResource: ${JSON.stringify(response)}`);

      // Extract request ID
      const requestId = extractRequestId(response) || "";

      // Extract session info from response (matching Python structure)
      const responseBody = response.body;
      const data = responseBody?.data; // Capital D to match Python

      const sessionInfo = new SessionInfoClass();

      if (data?.sessionId) {
        // Capital S and I to match Python
        sessionInfo.sessionId = data.sessionId;
      }

      if (data?.resourceUrl) {
        // Capital R and U to match Python
        sessionInfo.resourceUrl = data.resourceUrl;
      }

      // Transfer DesktopInfo fields to SessionInfo (matching Python structure)
      if (data?.desktopInfo) {
        // Capital D and I to match Python
        const desktopInfo = data.desktopInfo;
        if (desktopInfo.appId) {
          sessionInfo.appId = desktopInfo.appId;
        }
        if (desktopInfo.authCode) {
          sessionInfo.authCode = desktopInfo.authCode;
        }
        if (desktopInfo.connectionProperties) {
          sessionInfo.connectionProperties = desktopInfo.connectionProperties;
        }
        if (desktopInfo.resourceId) {
          sessionInfo.resourceId = desktopInfo.resourceId;
        }
        if (desktopInfo.resourceType) {
          sessionInfo.resourceType = desktopInfo.resourceType;
        }
        if (desktopInfo.ticket) {
          sessionInfo.ticket = desktopInfo.ticket;
        }
      }

      return {
        requestId,
        success: true,
        data: sessionInfo,
      };
    } catch (error) {
      logError("Error calling GetMcpResource:", error);
      throw new Error(
        `Failed to get session info for session ${this.sessionId}: ${error}`
      );
    }
  }

  /**
   * Get a link associated with the current session.
   *
   * @param protocolType - Optional protocol type to use for the link
   * @param port - Optional port to use for the link (must be in range [30100, 30199])
   * @returns OperationResult containing the link as data and request ID
   * @throws Error if the operation fails (matching Python SessionError)
   */
  async getLink(
    protocolType?: string,
    port?: number
  ): Promise<OperationResult> {
    try {
      // Validate port range if port is provided
      if (port) {
        if (!Number.isInteger(port) || port < 30100 || port > 30199) {
          throw new Error(
            `Invalid port value: ${port}. Port must be an integer in the range [30100, 30199].`
          );
        }
      }

      const request = new GetLinkRequest({
        authorization: `Bearer ${this.getAPIKey()}`,
        sessionId: this.getSessionId(),
        protocolType,
        port,
      });

      const response = await this.agentBay.getClient().getLink(request);

      // Extract request ID
      const requestId = extractRequestId(response) || "";

      const responseBody = response.body;

      if (typeof responseBody !== "object") {
        throw new Error(
          "Invalid response format: expected a dictionary from response body"
        );
      }

      let data = responseBody.data || {}; // Capital D to match Python
      log(`Data: ${JSON.stringify(data)}`);

      if (typeof data !== "object") {
        try {
          data = typeof data === "string" ? JSON.parse(data) : {};
        } catch (jsonError) {
          data = {};
        }
      }

      const url = (data as any).Url || (data as any).url;

      return {
        requestId,
        success: true,
        data: url,
      };
    } catch (error) {
      if (
        error instanceof Error &&
        error.message.includes("Invalid response format")
      ) {
        throw error;
      }
      throw new Error(`Failed to get link: ${error}`);
    }
  }

  /**
   * Asynchronously get a link associated with the current session.
   *
   * @param protocolType - Optional protocol type to use for the link
   * @param port - Optional port to use for the link (must be in range [30100, 30199])
   * @returns OperationResult containing the link as data and request ID
   * @throws Error if the operation fails (matching Python SessionError)
   */
  async getLinkAsync(
    protocolType?: string,
    port?: number
  ): Promise<OperationResult> {
    try {
      // Validate port range if port is provided
      if (port !== undefined) {
        if (!Number.isInteger(port) || port < 30100 || port > 30199) {
          throw new Error(
            `Invalid port value: ${port}. Port must be an integer in the range [30100, 30199].`
          );
        }
      }

      const request = new GetLinkRequest({
        authorization: `Bearer ${this.getAPIKey()}`,
        sessionId: this.getSessionId(),
        protocolType,
        port,
      });

      // Note: In TypeScript, async is the default, but keeping this method for API compatibility
      const response = await this.agentBay.getClient().getLink(request);

      // Extract request ID
      const requestId = extractRequestId(response) || "";

      const responseBody = response?.body;

      if (typeof responseBody !== "object") {
        throw new Error(
          "Invalid response format: expected a dictionary from response body"
        );
      }

      let data = responseBody?.data || {}; // Capital D to match Python
      log(`Data: ${JSON.stringify(data)}`);

      if (typeof data !== "object") {
        try {
          data = typeof data === "string" ? JSON.parse(data) : {};
        } catch (jsonError) {
          data = {};
        }
      }

      const url = (data as any).Url || (data as any).url;

      return {
        requestId,
        success: true,
        data: url,
      };
    } catch (error) {
      if (
        error instanceof Error &&
        error.message.includes("Invalid response format")
      ) {
        throw error;
      }
      throw new Error(`Failed to get link asynchronously: ${error}`);
    }
  }

  /**
   * List MCP tools available for this session.
   *
   * @param imageId Optional image ID, defaults to session's imageId or "linux_latest"
   * @returns McpToolsResult containing tools list and request ID
   */
  async listMcpTools(imageId?: string): Promise<McpToolsResult> {
    // Use provided imageId, session's imageId, or default
    if (!imageId) {
      imageId = (this as any).imageId || "linux_latest";
    }

    const request = new ListMcpToolsRequest({
      authorization: `Bearer ${this.getAPIKey()}`,
      imageId: imageId,
    });

    log("API Call: ListMcpTools");
    log(`Request: ImageId=${imageId}`);

    const response = await this.getClient().listMcpTools(request);

    // Extract request ID
    const requestId = extractRequestId(response) || "";

    if (response && response.body) {
      log("Response from ListMcpTools:", response.body);
    }

    // Parse the response data
    const tools: McpTool[] = [];
    if (response && response.body && response.body.data) {
      try {
        const toolsData = JSON.parse(response.body.data as string);
        for (const toolData of toolsData) {
          const tool: McpTool = {
            name: toolData.name || "",
            description: toolData.description || "",
            inputSchema: toolData.inputSchema || {},
            server: toolData.server || "",
            tool: toolData.tool || "",
          };
          tools.push(tool);
        }
      } catch (error) {
        logError(`Error unmarshaling tools data: ${error}`);
      }
    }

    this.mcpTools = tools; // Update the session's mcpTools field

    return {
      requestId,
      success: true,
      tools,
    };
  }

  /**
   * Call an MCP tool and return the result in a format compatible with Agent.
   *
   * @param toolName - Name of the MCP tool to call
   * @param args - Arguments to pass to the tool
   * @returns McpToolResult containing the response data
   */
  async callMcpTool(toolName: string, args: any): Promise<import("./agent/agent").McpToolResult> {
    try {
      const argsJSON = JSON.stringify(args);

      // Check if this is a VPC session
      if (this.isVpcEnabled()) {
        // VPC mode: Use HTTP request to the VPC endpoint
        const server = this.findServerForTool(toolName);
        if (!server) {
          return {
            success: false,
            data: "",
            errorMessage: `Server not found for tool: ${toolName}`,
            requestId: "",
          };
        }

        if (!this.networkInterfaceIp || !this.httpPort) {
          return {
            success: false,
            data: "",
            errorMessage: `VPC network configuration incomplete: networkInterfaceIp=${this.networkInterfaceIp}, httpPort=${this.httpPort}. This may indicate the VPC session was not properly configured with network parameters.`,
            requestId: "",
          };
        }

        const baseURL = `http://${this.networkInterfaceIp}:${this.httpPort}/callTool`;
        const url = new URL(baseURL);
        url.searchParams.append("server", server);
        url.searchParams.append("tool", toolName);
        url.searchParams.append("args", argsJSON);
        url.searchParams.append("token", this.getToken());
        // Add requestId for debugging purposes
        const requestId = `vpc-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        url.searchParams.append("requestId", requestId);

        const response = await fetch(url.toString(), {
          method: "GET",
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
          },
        });

        if (!response.ok) {
          return {
            success: false,
            data: "",
            errorMessage: `VPC request failed: ${response.statusText}`,
            requestId: "",
          };
        }

                 const responseData = await response.json() as any;

         // Extract the actual result from the nested VPC response structure
         let actualResult: any = responseData;
         if (typeof responseData.data === "string") {
           try {
             const dataMap = JSON.parse(responseData.data);
             if (dataMap.result) {
               actualResult = dataMap.result;
             }
           } catch (err) {
             // Keep original response if parsing fails
           }
         } else if (responseData.data && responseData.data.result) {
           actualResult = responseData.data.result;
         }

         // Extract text content from the result
         let textContent = "";
         if (actualResult.content && Array.isArray(actualResult.content) && actualResult.content.length > 0) {
           const contentItem = actualResult.content[0];
           if (contentItem && contentItem.text) {
             textContent = contentItem.text;
           }
         }

        return {
          success: true,
          data: textContent || JSON.stringify(actualResult),
          errorMessage: "",
          requestId: "",
        };
      } else {
        // Non-VPC mode: use traditional API call
        const callToolRequest = new CallMcpToolRequest({
          authorization: `Bearer ${this.getAPIKey()}`,
          sessionId: this.getSessionId(),
          name: toolName,
          args: argsJSON,
        });

        const response = await this.getClient().callMcpTool(callToolRequest);

        if (!response.body?.data) {
          return {
            success: false,
            data: "",
            errorMessage: "Invalid response data format",
            requestId: extractRequestId(response) || "",
          };
        }

        // Check for API-level errors before parsing Data
        if (response.body.success === false && response.body.code) {
          const errorMessage = `[${response.body.code}] ${response.body.message || 'Unknown error'}`;
          return {
            success: false,
            data: "",
            errorMessage,
            requestId: extractRequestId(response) || "",
          };
        }

        const data = response.body.data as Record<string, any>;

        // Check if there's an error in the response
        if (data.isError) {
          const errorContent = data.content || [];
          const errorMessage = errorContent
            .map((item: any) => item.text || "Unknown error")
            .join("; ");

          return {
            success: false,
            data: "",
            errorMessage,
            requestId: extractRequestId(response) || "",
          };
        }

        // Extract text content from content array
        const content = data.content || [];
        let textContent = "";
        if (content.length > 0 && content[0].text !== undefined) {
          textContent = content[0].text;
        }

        return {
          success: true,
          data: textContent,
          errorMessage: "",
          requestId: extractRequestId(response) || "",
        };
      }
    } catch (error) {
      return {
        success: false,
        data: "",
        errorMessage: error instanceof Error ? error.message : String(error),
        requestId: "",
      };
    }
  }
}
