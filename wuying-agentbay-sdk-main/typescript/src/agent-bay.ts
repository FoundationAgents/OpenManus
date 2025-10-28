import { $OpenApiUtil } from "@alicloud/openapi-core";
import "dotenv/config";
import * as $_client from "./api";
import { ListSessionRequest, CreateMcpSessionRequestPersistenceDataList, GetSessionRequest as $GetSessionRequest } from "./api/models/model";
import { Client } from "./api/client";

import { loadConfig, loadDotEnvWithFallback, Config, BROWSER_DATA_PATH } from "./config";
import { ContextService } from "./context";
import { ContextSync } from "./context-sync";
import { APIError, AuthenticationError } from "./exceptions";
import { Session } from "./session";
import { BrowserContext } from "./session-params";
import { Context } from "./context";

import {
  DeleteResult,
  extractRequestId,
  GetSessionResult as $GetSessionResult,
  SessionResult,
} from "./types/api-response";
import {
  ListSessionParams,
  SessionListResult,
} from "./types/list-session-params";
import { log, logError } from "./utils/logger";

/**
 * Generate a random context name using alphanumeric characters with timestamp.
 * This function is similar to the Python version's generate_random_context_name.
 */
function generateRandomContextName(length = 8, includeTimestamp = true): string {
  const timestamp = new Date().toISOString().replace(/[-T:.Z]/g, '').slice(0, 14);

  const characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  let randomPart = '';
  for (let i = 0; i < length; i++) {
    randomPart += characters.charAt(Math.floor(Math.random() * characters.length));
  }

  return includeTimestamp ? `${timestamp}_${randomPart}` : randomPart;
}

/**
 * Parameters for creating a session.
 */
export interface CreateSessionParams {
  labels?: Record<string, string>;
  imageId?: string;
  contextSync?: ContextSync[];
  browserContext?: BrowserContext;
  isVpc?: boolean;
  policyId?: string;
  enableBrowserReplay?: boolean;
}

/**
 * Main class for interacting with the AgentBay cloud runtime environment.
 */
export class AgentBay {
  private apiKey: string;
  private client: Client;
  private endpoint: string;
  private sessions: Map<string, Session> = new Map();
  private fileTransferContext: Context | null = null;

  /**
   * Context service for managing persistent contexts.
   */
  context: ContextService;

  /**
   * Initialize the AgentBay client.
   *
   * @param options - Configuration options
   * @param options.apiKey - API key for authentication. If not provided, will look for AGENTBAY_API_KEY environment variable.
   * @param options.config - Custom configuration object. If not provided, will use environment-based configuration.
   * @param options.envFile - Custom path to .env file. If not provided, will search upward from current directory.
   */
  constructor(
    options: {
      apiKey?: string;
      config?: Config;
      envFile?: string;
    } = {}
  ) {
    // Load .env file first to ensure AGENTBAY_API_KEY is available
    loadDotEnvWithFallback(options.envFile);

    this.apiKey = options.apiKey || process.env.AGENTBAY_API_KEY || "";

    if (!this.apiKey) {
      throw new AuthenticationError(
        "API key is required. Provide it as a parameter or set the AGENTBAY_API_KEY environment variable."
      );
    }

    // Load configuration using the enhanced loadConfig function
    const configData = loadConfig(options.config, options.envFile);
    this.endpoint = configData.endpoint;

    const config = new $OpenApiUtil.Config({
      regionId: "",
      endpoint: this.endpoint,
    });

    config.readTimeout = configData.timeout_ms;
    config.connectTimeout = configData.timeout_ms;

    try {
      this.client = new Client(config);

      // Initialize context service
      this.context = new ContextService(this);
    } catch (error) {
      logError(`Failed to constructor:`, error);
      throw new AuthenticationError(`Failed to constructor: ${error}`);
    }
  }

  /**
   * Update browser replay context with AppInstanceId from response data.
   *
   * @param responseData - Response data containing AppInstanceId
   * @param recordContextId - The record context ID to update
   */
  private async _updateBrowserReplayContext(responseData: any, recordContextId: string): Promise<void> {
    // Check if record_context_id is provided
    if (!recordContextId) {
      return;
    }

    try {
      // Extract AppInstanceId from response data
      const appInstanceId = responseData?.appInstanceId;
      if (!appInstanceId) {
        logError("AppInstanceId not found in response data, skipping browser replay context update");
        return;
      }

      // Create context name with prefix
      const contextName = `browserreplay-${appInstanceId}`;

      // Create Context object for update
      const contextObj = new Context(recordContextId, contextName);

      // Call context.update interface
      log(`Updating browser replay context: ${contextName} -> ${recordContextId}`);
      const updateResult = await this.context.update(contextObj);

      if (updateResult.success) {
        log(`✅ Successfully updated browser replay context: ${contextName}`);
      } else {
        logError(`⚠️ Failed to update browser replay context: ${updateResult.errorMessage}`);
      }
    } catch (error) {
      logError(`❌ Error updating browser replay context: ${error}`);
      // Continue execution even if context update fails
    }
  }

  /**
   * Create a new session in the AgentBay cloud environment.
   *
   * @param params - Optional parameters for creating the session
   * @returns SessionResult containing the created session and request ID
   */
  async create(params: CreateSessionParams = {}): Promise<SessionResult> {
    try {
      // Create a default context for file transfer operations if none provided
      // and no context_syncs are specified
      const contextName = `file-transfer-context-${Date.now()}`;
      const contextResult = await this.context.get(contextName, true);
      if (contextResult.success && contextResult.context) {
        this.fileTransferContext = contextResult.context;
        // Add the context to the session params for file transfer operations
        const fileTransferContextSync = new ContextSync(
          contextResult.context.id,
          "/temp/file-transfer"
        );
        if (!params.contextSync) {
          params.contextSync = [];
        }
        log(`Adding context sync for file transfer operations: ${fileTransferContextSync}`);
        params.contextSync.push(fileTransferContextSync);
      }

      const request = new $_client.CreateMcpSessionRequest({
        authorization: "Bearer " + this.apiKey,
      });

      // Add labels if provided
      if (params.labels) {
        request.labels = JSON.stringify(params.labels);
      }

      // Add image_id if provided
      if (params.imageId) {
        request.imageId = params.imageId;
      }

      // Add PolicyId if provided
      if (params.policyId) {
        request.mcpPolicyId = params.policyId;
      }

      // Add VPC resource if specified
      request.vpcResource = params.isVpc || false;

      // Flag to indicate if we need to wait for context synchronization
      let needsContextSync = false;

      // Add context sync configurations if provided
      if (params.contextSync && params.contextSync.length > 0) {
        const persistenceDataList: CreateMcpSessionRequestPersistenceDataList[] = [];
        for (const contextSync of params.contextSync) {
          const persistenceItem = new CreateMcpSessionRequestPersistenceDataList({
            contextId: contextSync.contextId,
            path: contextSync.path,
          });

          // Convert policy to JSON string if provided
          if (contextSync.policy) {
            persistenceItem.policy = JSON.stringify(contextSync.policy);
          }

          persistenceDataList.push(persistenceItem);
        }
        request.persistenceDataList = persistenceDataList;
        needsContextSync = persistenceDataList.length > 0;
      }

      // Add BrowserContext as a ContextSync if provided
      if (params.browserContext) {
        // Create a simple sync policy for browser context
        const syncPolicy = {
          uploadPolicy: { autoUpload: params.browserContext.autoUpload },
          downloadPolicy: null,
          deletePolicy: null,
          bwList: null,
          recyclePolicy: null,
        };

        // Create browser context sync item
        const browserContextSync = new CreateMcpSessionRequestPersistenceDataList({
          contextId: params.browserContext.contextId,
          path: BROWSER_DATA_PATH, // Using a constant path for browser data
          policy: JSON.stringify(syncPolicy)
        });

        // Add to persistence data list or create new one if not exists
        if (!request.persistenceDataList) {
          request.persistenceDataList = [];
        }
        request.persistenceDataList.push(browserContextSync);
        needsContextSync = true;
      }

      // Add browser recording persistence if enabled
      let recordContextId = ""; // Initialize record_context_id
      if (params.enableBrowserReplay) {
        // Create browser recording persistence configuration
        const recordPath = "/home/guest/record";
        const recordContextName = generateRandomContextName();
        const result = await this.context.get(recordContextName, true);
        recordContextId = result.success ? result.contextId : "";
        const recordPersistence = new CreateMcpSessionRequestPersistenceDataList({
          contextId: recordContextId,
          path: recordPath,
        });

        // Add to persistence data list or create new one if not exists
        if (!request.persistenceDataList) {
          request.persistenceDataList = [];
        }
        request.persistenceDataList.push(recordPersistence);
      }

      // Log API request
      log("API Call: CreateMcpSession");
      let requestLog = "Request: ";
      if (request.imageId) {
        requestLog += `ImageId=${request.imageId}, `;
      }
      if (request.labels) {
        requestLog += `Labels=${request.labels}, `;
      }
      if (
        request.persistenceDataList &&
        request.persistenceDataList.length > 0
      ) {
        requestLog += `PersistenceDataList=${request.persistenceDataList.length} items, `;
        request.persistenceDataList.forEach((pd: CreateMcpSessionRequestPersistenceDataList, i: number) => {
          requestLog += `Item${i}[ContextId=${pd.contextId}, Path=${pd.path}`;
          if (pd.policy) {
            requestLog += `, Policy=${pd.policy}`;
          }
          requestLog += `], `;
        });
      }
      log(requestLog);

      const response = await this.client.createMcpSession(request);

      // Extract request ID
      const requestId = extractRequestId(response) || "";

      // Log response data with requestId
      log("response data =", response.body?.data);
      if (requestId) {
        log(`requestId = ${requestId}`);
      }

      const sessionData = response.body;

      if (!sessionData || typeof sessionData !== "object") {
        return {
          requestId,
          success: false,
          errorMessage: "Invalid response format: expected a dictionary",
        };
      }

      // Check for API-level errors
      if (sessionData.success === false && sessionData.code) {
        const errorMessage = `[${sessionData.code}] ${sessionData.message || 'Unknown error'}`;
        return {
          requestId,
          success: false,
          errorMessage,
        };
      }

      const data = sessionData.data;
      if (!data || typeof data !== "object") {
        return {
          requestId,
          success: false,
          errorMessage:
            "Invalid response format: 'data' field is not a dictionary",
        };
      }

      const sessionId = data.sessionId;
      if (!sessionId) {
        return {
          requestId,
          success: false,
          errorMessage: "SessionId not found in response",
        };
      }

      // ResourceUrl is optional in CreateMcpSession response
      const resourceUrl = data.resourceUrl || "";

      log("session_id =", sessionId);
      log("resource_url =", resourceUrl);

      const session = new Session(this, sessionId);

      // Set VPC-related information from response
      session.isVpc = params.isVpc || false;
      if (data.networkInterfaceIp) {
        session.networkInterfaceIp = data.networkInterfaceIp;
      }
      if (data.httpPort) {
        session.httpPort = data.httpPort;
      }
      if (data.token) {
        session.token = data.token;
      }

      // Set ResourceUrl
      session.resourceUrl = resourceUrl;

      // Set browser recording state
      session.enableBrowserReplay = params.enableBrowserReplay || false;

      // Store the file transfer context ID if we created one
      session.fileTransferContextId = this.fileTransferContext ? this.fileTransferContext.id : null;
      // Store imageId used for this session
      (session as any).imageId = params.imageId;

      this.sessions.set(session.sessionId, session);

      // Update browser replay context if enabled
      if (params.enableBrowserReplay) {
        await this._updateBrowserReplayContext(data, recordContextId);
      }

      // For VPC sessions, automatically fetch MCP tools information
      if (params.isVpc) {
        log("VPC session detected, automatically fetching MCP tools...");
        try {
          const toolsResult = await session.listMcpTools();
          log(`Successfully fetched ${toolsResult.tools.length} MCP tools for VPC session (RequestID: ${toolsResult.requestId})`);
        } catch (error) {
          logError(`Warning: Failed to fetch MCP tools for VPC session: ${error}`);
          // Continue with session creation even if tools fetch fails
        }
      }

      // If we have persistence data, wait for context synchronization
      if (needsContextSync) {
        log("Waiting for context synchronization to complete...");

        // Wait for context synchronization to complete
        const maxRetries = 150; // Maximum number of retries
        const retryInterval = 1500; // Milliseconds to wait between retries

        for (let retry = 0; retry < maxRetries; retry++) {
          try {
            // Get context status data
            const infoResult = await session.context.info();

            // Check if all context items have status "Success" or "Failed"
            let allCompleted = true;
            let hasFailure = false;

            for (const item of infoResult.contextStatusData) {
              log(`Context ${item.contextId} status: ${item.status}, path: ${item.path}`);

              if (item.status !== "Success" && item.status !== "Failed") {
                allCompleted = false;
                break;
              }

              if (item.status === "Failed") {
                hasFailure = true;
                logError(`Context synchronization failed for ${item.contextId}: ${item.errorMessage}`);
              }
            }

            if (allCompleted || infoResult.contextStatusData.length === 0) {
              if (hasFailure) {
                log("Context synchronization completed with failures");
              } else {
                log("Context synchronization completed successfully");
              }
              break;
            }

            log(`Waiting for context synchronization, attempt ${retry+1}/${maxRetries}`);
            await new Promise(resolve => setTimeout(resolve, retryInterval));
          } catch (error) {
            logError(`Error checking context status on attempt ${retry+1}: ${error}`);
            await new Promise(resolve => setTimeout(resolve, retryInterval));
          }
        }
      }

      // Return SessionResult with request ID
      return {
        requestId,
        success: true,
        session,
      };
    } catch (error) {
      logError("Error calling create_mcp_session:", error);
      return {
        requestId: "",
        success: false,
        errorMessage: `Failed to create session: ${error}`,
      };
    }
  }


  /**
   * List sessions filtered by the provided labels with pagination support.
   * It returns sessions that match all the specified labels.
   *
   * @deprecated This method is deprecated and will be removed in a future version. Use list() instead.
   *
   * **Breaking Change**: This method currently only accepts ListSessionParams parameters，
   *
   * @param params - Parameters including labels and pagination options (required)
   * @returns API response with sessions list and pagination info
   */
  async listByLabels(params?: ListSessionParams): Promise<SessionListResult> {
    if (!params) {
      params = {
        maxResults: 10,
        labels: {},
      };
    }

    try {
      // Convert labels to JSON
      const labelsJSON = JSON.stringify(params.labels);

      //Build request object with support for pagination parameters
      const listSessionRequest = new ListSessionRequest({
        authorization: `Bearer ${this.apiKey}`,
        labels: labelsJSON,
        maxResults: params.maxResults || 10,
        ...(params.nextToken && { nextToken: params.nextToken }),
      });

      log("API Call: ListSession");
      log(
        `Request: Labels=${labelsJSON}, MaxResults=${params.maxResults || 10}${
          params.nextToken ? `, NextToken=${params.nextToken}` : ""
        }`
      );

      const response = await this.client.listSession(listSessionRequest);
      const body = response.body;
      const requestId = extractRequestId(body?.requestId) || "";

      // Check for errors in the response
      if (
        body?.data &&
        typeof body.data === "object" &&
        body.success &&
        body.success !== true
      ) {
        return {
          requestId,
          success: false,
          errorMessage: "Failed to list sessions by labels",
          sessionIds: [],
          nextToken: "",
          maxResults: params.maxResults || 10,
          totalCount: 0,
        };
      }

      const sessionIds: string[] = [];
      let nextToken = "";
      let maxResults = params.maxResults || 10;
      let totalCount = 0;

      log("body =", body);

      // Extract pagination information
      if (body && typeof body === "object") {
        nextToken = body.nextToken || "";
        maxResults = parseInt(String(body.maxResults || 0)) || maxResults;
        totalCount = parseInt(String(body.totalCount || 0));
      }

      // Extract session data
      const responseData = body?.data;

      // Handle both list and dict responses
      if (Array.isArray(responseData)) {
        // Data is a list of session objects
        for (const sessionData of responseData) {
          if (sessionData && typeof sessionData === "object") {
            const sessionId = (sessionData as any).sessionId; // Capital S and I to match Python
            if (sessionId) {
              sessionIds.push(sessionId);
            }
          }
        }
      }

      // Return SessionListResult with request ID and pagination info
      return {
        requestId,
        success: true,
        sessionIds,
        nextToken,
        maxResults,
        totalCount,
      };
    } catch (error) {
      logError("Error calling list_session:", error);
      return {
        requestId: "",
        success: false,
        sessionIds: [],
        errorMessage: `Failed to list sessions by labels: ${error}`,
      };
    }
  }

  /**
   * Returns paginated list of session IDs filtered by labels.
   *
   * @param labels - Optional labels to filter sessions (defaults to empty object)
   * @param page - Optional page number for pagination (starting from 1, defaults to 1)
   * @param limit - Optional maximum number of items per page (defaults to 10)
   * @returns SessionListResult - Paginated list of session IDs that match the labels
   *
   * @example
   * ```typescript
   * const agentBay = new AgentBay({ apiKey: "your_api_key" });
   *
   * // List all sessions
   * const result = await agentBay.list();
   *
   * // List sessions with specific labels
   * const result = await agentBay.list({ project: "demo" });
   *
   * // List sessions with pagination
   * const result = await agentBay.list({ "my-label": "my-value" }, 2, 10);
   *
   * if (result.success) {
   *   for (const sessionId of result.sessionIds) {
   *     console.log(`Session ID: ${sessionId}`);
   *   }
   *   console.log(`Total count: ${result.totalCount}`);
   *   console.log(`Request ID: ${result.requestId}`);
   * }
   * ```
   */
  async list(
    labels: Record<string, string> = {},
    page?: number,
    limit: number = 10
  ): Promise<SessionListResult> {
    try {
      // Validate page number
      if (page !== undefined && page < 1) {
        return {
          requestId: "",
          success: false,
          errorMessage: `Cannot reach page ${page}: Page number must be >= 1`,
          sessionIds: [],
          nextToken: "",
          maxResults: limit,
          totalCount: 0,
        };
      }

      // Calculate next_token based on page number
      // Page 1 or undefined means no next_token (first page)
      // For page > 1, we need to make multiple requests to get to that page
      let nextToken = "";
      if (page !== undefined && page > 1) {
        // We need to fetch pages 1 through page-1 to get the next_token
        let currentPage = 1;
        while (currentPage < page) {
          // Make API call to get next_token
          const request = new ListSessionRequest({
            authorization: `Bearer ${this.apiKey}`,
            labels: JSON.stringify(labels),
            maxResults: limit,
          });
          if (nextToken) {
            request.nextToken = nextToken;
          }

          const response = await this.client.listSession(request);
          const requestId = extractRequestId(response) || "";

          if (!response.body?.success) {
            const code = response.body?.code || "Unknown";
            const message = response.body?.message || "Unknown error";
            return {
              requestId,
              success: false,
              errorMessage: `[${code}] ${message}`,
              sessionIds: [],
              nextToken: "",
              maxResults: limit,
              totalCount: 0,
            };
          }

          nextToken = response.body.nextToken || "";
          if (!nextToken) {
            // No more pages available
            return {
              requestId,
              success: false,
              errorMessage: `Cannot reach page ${page}: No more pages available`,
              sessionIds: [],
              nextToken: "",
              maxResults: limit,
              totalCount: response.body.totalCount || 0,
            };
          }
          currentPage += 1;
        }
      }

      // Make the actual request for the desired page
      const request = new ListSessionRequest({
        authorization: `Bearer ${this.apiKey}`,
        labels: JSON.stringify(labels),
        maxResults: limit,
      });
      if (nextToken) {
        request.nextToken = nextToken;
      }

      // Log API request
      log("API Call: ListSession");
      log(`Request: Labels=${JSON.stringify(labels)}, MaxResults=${limit}${nextToken ? `, NextToken=${nextToken}` : ""}`);

      const response = await this.client.listSession(request);

      // Log API response
      log("body =", response.body);

      // Extract request ID
      const requestId = extractRequestId(response) || "";

      // Check for errors in the response
      if (!response.body?.success) {
        const code = response.body?.code || "Unknown";
        const message = response.body?.message || "Unknown error";
        return {
          requestId,
          success: false,
          errorMessage: `[${code}] ${message}`,
          sessionIds: [],
          nextToken: "",
          maxResults: limit,
          totalCount: 0,
        };
      }

      const sessionIds: string[] = [];

      // Extract session data
      if (response.body.data) {
        for (const sessionData of response.body.data) {
          if (sessionData.sessionId) {
            sessionIds.push(sessionData.sessionId);
          }
        }
      }

      // Return SessionListResult with request ID and pagination info
      return {
        requestId,
        success: true,
        sessionIds,
        nextToken: response.body.nextToken || "",
        maxResults: response.body.maxResults || limit,
        totalCount: response.body.totalCount || 0,
      };
    } catch (error) {
      logError("Error calling list_session:", error);
      return {
        requestId: "",
        success: false,
        errorMessage: `Failed to list sessions: ${error}`,
        sessionIds: [],
      };
    }
  }

  /**
   * Delete a session by session object.
   *
   * @param session - The session to delete.
   * @param syncContext - Whether to sync context data (trigger file uploads) before deleting the session. Defaults to false.
   * @returns DeleteResult indicating success or failure and request ID
   */
  async delete(session: Session, syncContext = false): Promise<DeleteResult> {
    try {
      // Delete the session and get the result
      if (session.enableBrowserReplay) {
        syncContext = true;
      }
      const deleteResult = await session.delete(syncContext);

      this.sessions.delete(session.sessionId);

      // Return the DeleteResult obtained from session.delete()
      return deleteResult;
    } catch (error) {
      logError("Error deleting session:", error);
      return {
        requestId: "",
        success: false,
        errorMessage: `Failed to delete session ${session.sessionId}: ${error}`,
      };
    }
  }

  /**
   *
   * @param sessionId - The ID of the session to remove.
   */
  public removeSession(sessionId: string): void {
    this.sessions.delete(sessionId);
  }

  /**
   * Get session information by session ID.
   *
   * @param sessionId - The ID of the session to retrieve.
   * @returns GetSessionResult containing session information
   */
  async getSession(sessionId: string): Promise<$GetSessionResult> {
    try {
      log("API Call: GetSession");
      log(`Request: SessionId=${sessionId}`);

      const request = new $GetSessionRequest({
        authorization: `Bearer ${this.apiKey}`,
        sessionId: sessionId,
      });

      const response = await this.client.getSession(request);

      log("Response from GetSession:", response.body);

      const requestId = extractRequestId(response) || "";
      const body = response.body;

      // Check for API-level errors
      if (body?.success === false && body.code) {
        return {
          requestId,
          httpStatusCode: body.httpStatusCode || 0,
          code: body.code,
          success: false,
          errorMessage: `[${body.code}] ${body.message || 'Unknown error'}`,
        };
      }

      const result: $GetSessionResult = {
        requestId,
        httpStatusCode: body?.httpStatusCode || 0,
        code: body?.code || "",
        success: body?.success || false,
        errorMessage: "",
      };

      if (body?.data) {
        result.data = {
          appInstanceId: body.data.appInstanceId || "",
          resourceId: body.data.resourceId || "",
          sessionId: body.data.sessionId || "",
          success: body.data.success || false,
          httpPort: body.data.httpPort || "",
          networkInterfaceIp: body.data.networkInterfaceIp || "",
          token: body.data.token || "",
          vpcResource: body.data.vpcResource || false,
          resourceUrl: body.data.resourceUrl || "",
        };
      }

      return result;
    } catch (error) {
      logError("Error calling GetSession:", error);
      return {
        requestId: "",
        httpStatusCode: 0,
        code: "",
        success: false,
        errorMessage: `Failed to get session ${sessionId}: ${error}`,
      };
    }
  }

  /**
   * Get a session by its ID.
   *
   * This method retrieves a session by calling the GetSession API
   * and returns a SessionResult containing the Session object and request ID.
   *
   * @param sessionId - The ID of the session to retrieve
   * @returns Promise resolving to SessionResult with the Session instance, request ID, and success status
   *
   * @example
   * ```typescript
   * const result = await agentBay.get("my-session-id");
   * if (result.success) {
   *   console.log(result.session.sessionId);
   *   console.log(result.requestId);
   * }
   * ```
   */
  async get(sessionId: string): Promise<SessionResult> {
    // Validate input
    if (
      !sessionId ||
      (typeof sessionId === "string" && !sessionId.trim())
    ) {
      return {
        requestId: "",
        success: false,
        errorMessage: "session_id is required",
      };
    }

    // Call GetSession API
    const getResult = await this.getSession(sessionId);

    // Check if the API call was successful
    if (!getResult.success) {
      const errorMsg = getResult.errorMessage || "Unknown error";
      return {
        requestId: getResult.requestId,
        success: false,
        errorMessage: `Failed to get session ${sessionId}: ${errorMsg}`,
      };
    }

    // Create the Session object
    const session = new Session(this, sessionId);

    // Set VPC-related information and ResourceUrl from GetSession response
    if (getResult.data) {
      session.isVpc = getResult.data.vpcResource;
      session.networkInterfaceIp = getResult.data.networkInterfaceIp;
      session.httpPort = getResult.data.httpPort;
      session.token = getResult.data.token;
      session.resourceUrl = getResult.data.resourceUrl;
    }

    return {
      requestId: getResult.requestId,
      success: true,
      session,
    };
  }

  // For internal use by the Session class
  getClient(): Client {
    return this.client;
  }

  getAPIKey(): string {
    return this.apiKey;
  }
}

/**
 * Creates a new AgentBay client using default configuration.
 * This is a convenience function that allows creating an AgentBay instance without a config parameter.
 *
 * @param apiKey - API key for authentication
 * @returns A new AgentBay instance with default configuration
 */
export function newAgentBayWithDefaults(apiKey: string): AgentBay {
  return new AgentBay({ apiKey });
}
