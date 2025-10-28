import { AgentBay } from "./agent-bay";
import { APIError } from "./exceptions";
import * as $_client from "./api";
import { log, logError } from "./utils/logger";
import {
  extractRequestId,
  ContextResult,
  ContextListResult,
  OperationResult,
  FileUrlResult,
  ContextFileListResult,
  ContextFileEntry,
} from "./types/api-response";

/**
 * Represents a persistent storage context in the AgentBay cloud environment.
 */
export class Context {
  /**
   * The unique identifier of the context.
   */
  id: string;

  /**
   * The name of the context.
   */
  name: string;

  /**
   * @deprecated This field is no longer used and will be removed in a future version.
   */
  state: string;

  /**
   * Date and time when the Context was created.
   */
  createdAt?: string;

  /**
   * Date and time when the Context was last used.
   */
  lastUsedAt?: string;

  /**
   * @deprecated This field is no longer used and will be removed in a future version.
   */
  osType?: string;

  /**
   * Initialize a Context object.
   *
   * @param id - The unique identifier of the context.
   * @param name - The name of the context.
   * @param state - **Deprecated.** This parameter is no longer used.
   * @param createdAt - Date and time when the Context was created.
   * @param lastUsedAt - Date and time when the Context was last used.
   * @param osType - **Deprecated.** This parameter is no longer used.
   */
  constructor(
    id: string,
    name: string,
    state = "available",
    createdAt?: string,
    lastUsedAt?: string,
    osType?: string
  ) {
    this.id = id;
    this.name = name;
    this.state = state;
    this.createdAt = createdAt;
    this.lastUsedAt = lastUsedAt;
    this.osType = osType;
  }
}

/**
 * Parameters for listing contexts with pagination support.
 */
export interface ContextListParams {
  /**
   * Maximum number of results per page.
   * Defaults to 10 if not specified.
   */
  maxResults?: number;

  /**
   * Token for the next page of results.
   */
  nextToken?: string;
}

/**
 * Provides methods to manage persistent contexts in the AgentBay cloud environment.
 */
export class ContextService {
  private agentBay: AgentBay;

  /**
   * Initialize the ContextService.
   *
   * @param agentBay - The AgentBay instance.
   */
  constructor(agentBay: AgentBay) {
    this.agentBay = agentBay;
  }

  /**
   * Lists all available contexts with pagination support.
   * Corresponds to Python's list() method
   *
   * @param params - Optional parameters for listing contexts.
   * @returns ContextListResult with contexts list and pagination information
   */
  async list(params?: ContextListParams): Promise<ContextListResult> {
    try {
      // Set default maxResults if not specified
      const maxResults = params?.maxResults !== undefined ? params.maxResults : 10;

      const request = new $_client.ListContextsRequest({
        authorization: `Bearer ${this.agentBay.getAPIKey()}`,
        maxResults: maxResults,
        nextToken: params?.nextToken,
      });

      // Log API request
      log("API Call: ListContexts");
      log(`Request: MaxResults=${maxResults}`, params?.nextToken ? `, NextToken=${params.nextToken}` : "");

      const response = await this.agentBay.getClient().listContexts(request);

      // Log API response
      log(`Response from ListContexts:`, response.body);

      // Check for API-level errors
      if (response.body?.success === false && response.body?.code) {
        const errorMessage = `[${response.body.code}] ${response.body.message || 'Unknown error'}`;
        return {
          requestId: extractRequestId(response) || "",
          success: false,
          contexts: [],
          errorMessage,
        };
      }

      const contexts: Context[] = [];
      if (response.body?.data) {
        for (const contextData of response.body.data) {
          contexts.push(
            new Context(
              contextData.id || "",
              contextData.name || "",
              contextData.state || "available",
              contextData.createTime,
              contextData.lastUsedTime,
              contextData.osType
            )
          );
        }
      }

      return {
        requestId: extractRequestId(response) || "",
        success: true,
        contexts,
        nextToken: response.body?.nextToken,
        maxResults: response.body?.maxResults || maxResults,
        totalCount: response.body?.totalCount,
      };
    } catch (error) {
      logError("Error calling ListContexts:", error);
      return {
        requestId: "",
        success: false,
        contexts: [],
        errorMessage: `Failed to list contexts: ${error}`,
      };
    }
  }

  /**
   * Gets a context by name. Optionally creates it if it doesn't exist.
   * Corresponds to Python's get() method
   *
   * @param name - The name of the context to get.
   * @param create - Whether to create the context if it doesn't exist.
   * @returns ContextResult with context data and requestId
   */
  async get(name: string, create = false): Promise<ContextResult> {
    try {
      const request = new $_client.GetContextRequest({
        name: name,
        allowCreate: create ? "true" : "false",
        authorization: `Bearer ${this.agentBay.getAPIKey()}`,
      });

      // Log API request
      log("API Call: GetContext");
      log(`Request: Name=${name}, AllowCreate=${create}`);

      const response = await this.agentBay.getClient().getContext(request);

      // Log API response
      log(`Response from GetContext:`, response.body);

      // Check for API-level errors
      if (response.body?.success === false && response.body?.code) {
        const errorMessage = `[${response.body.code}] ${response.body.message || 'Unknown error'}`;
        return {
          requestId: extractRequestId(response) || "",
          success: false,
          contextId: "",
          context: undefined,
          errorMessage,
        };
      }

      const contextId = response.body?.data?.id || "";
      if (!contextId) {
        return {
          requestId: extractRequestId(response) || "",
          success: false,
          contextId: "",
          context: undefined,
          errorMessage: "Context ID not found in response",
        };
      }

      // Get the full context details
      const contextsResponse = await this.list();
      for (const context of contextsResponse.contexts) {
        if (context.id === contextId) {
          return {
            requestId: extractRequestId(response) || "",
            success: true,
            contextId,
            context,
          };
        }
      }

      // If we couldn't find the context in the list, create a basic one
      const context = new Context(contextId, name);
      return {
        requestId: extractRequestId(response) || "",
        success: true,
        contextId,
        context,
      };
    } catch (error) {
      logError("Error calling GetContext:", error);
      return {
        requestId: "",
        success: false,
        contextId: "",
        context: undefined,
        errorMessage: `Failed to get context ${name}: ${error}`,
      };
    }
  }

  /**
   * Creates a new context with the given name.
   * Corresponds to Python's create() method
   *
   * @param name - The name for the new context.
   * @returns ContextResult with created context data and requestId
   */
  async create(name: string): Promise<ContextResult> {
    return await this.get(name, true);
  }

  /**
   * Updates the specified context.
   * Corresponds to Python's update() method
   *
   * @param context - The Context object to update.
   * @returns OperationResult with updated context data and requestId
   */
  async update(context: Context): Promise<OperationResult> {
    try {
      const request = new $_client.ModifyContextRequest({
        id: context.id,
        name: context.name,
        authorization: `Bearer ${this.agentBay.getAPIKey()}`,
      });

      // Log API request
      log("API Call: ModifyContext");
      log(`Request: Id=${context.id}, Name=${context.name}`);

      const response = await this.agentBay.getClient().modifyContext(request);

      // Log API response
      log(`Response from ModifyContext:`, response.body);

      // Check for success (matching Python logic)
      const success = response.body?.success !== false;
      const errorMessage = success
        ? ""
        : `[${response.body?.code || 'Unknown'}] ${response.body?.message || 'Unknown error'}`;

      return {
        requestId: extractRequestId(response) || "",
        success,
        data: success,
        errorMessage,
      };
    } catch (error) {
      logError("Error calling ModifyContext:", error);
      return {
        requestId: "",
        success: false,
        errorMessage: `Failed to update context ${context.id}: ${error}`,
      };
    }
  }

  /**
   * Deletes the specified context.
   * Corresponds to Python's delete() method
   *
   * @param context - The Context object to delete.
   * @returns OperationResult with requestId
   */
  async delete(context: Context): Promise<OperationResult> {
    try {
      const request = new $_client.DeleteContextRequest({
        id: context.id,
        authorization: `Bearer ${this.agentBay.getAPIKey()}`,
      });

      // Log API request
      log("API Call: DeleteContext");
      log(`Request: Id=${context.id}`);

      const response = await this.agentBay.getClient().deleteContext(request);

      // Log API response
      log(`Response from DeleteContext:`, response.body);

      // Check for success (matching Python logic)
      const success = response.body?.success !== false;
      const errorMessage = success
        ? ""
        : `[${response.body?.code || 'Unknown'}] ${response.body?.message || 'Unknown error'}`;

      return {
        requestId: extractRequestId(response) || "",
        success,
        data: success,
        errorMessage,
      };
    } catch (error) {
      logError("Error calling DeleteContext:", error);
      return {
        requestId: "",
        success: false,
        errorMessage: `Failed to delete context ${context.id}: ${error}`,
      };
    }
  }

  /**
   * Get a presigned upload URL for a file in a context.
   */
  async getFileUploadUrl(contextId: string, filePath: string): Promise<FileUrlResult> {
    log("API Call: GetContextFileUploadUrl");
    log(`Request: ContextId=${contextId}, FilePath=${filePath}`);
    const req = new $_client.GetContextFileUploadUrlRequest({
      authorization: `Bearer ${this.agentBay.getAPIKey()}`,
      contextId,
      filePath,
    });
    const resp = await this.agentBay.getClient().getContextFileUploadUrl(req);
    log("Response from GetContextFileUploadUrl:", resp.body);
    const requestId = extractRequestId(resp) || "";
    const body = resp.body;

    // Check for API-level errors
    if (body?.success === false && body.code) {
      return {
        requestId,
        success: false,
        url: "",
        expireTime: undefined,
        errorMessage: `[${body.code}] ${body.message || 'Unknown error'}`,
      };
    }

    const data = body?.data;
    return {
      requestId,
      success: !!(body && body.success),
      url: data?.url || "",
      expireTime: data?.expireTime,
      errorMessage: undefined,
    };
  }

  /**
   * Get a presigned download URL for a file in a context.
   */
  async getFileDownloadUrl(contextId: string, filePath: string): Promise<FileUrlResult> {
    log("API Call: GetContextFileDownloadUrl");
    log(`Request: ContextId=${contextId}, FilePath=${filePath}`);
    const req = new $_client.GetContextFileDownloadUrlRequest({
      authorization: `Bearer ${this.agentBay.getAPIKey()}`,
      contextId,
      filePath,
    });
    const resp = await this.agentBay.getClient().getContextFileDownloadUrl(req);
    log("Response from GetContextFileDownloadUrl:", resp.body);
    const requestId = extractRequestId(resp) || "";
    const body = resp.body;

    // Check for API-level errors
    if (body?.success === false && body.code) {
      return {
        requestId,
        success: false,
        url: "",
        expireTime: undefined,
        errorMessage: `[${body.code}] ${body.message || 'Unknown error'}`,
      };
    }

    const data = body?.data;
    return {
      requestId,
      success: !!(body && body.success),
      url: data?.url || "",
      expireTime: data?.expireTime,
      errorMessage: undefined,
    };
  }

  /**
   * Delete a file in a context.
   */
  async deleteFile(contextId: string, filePath: string): Promise<OperationResult> {
    log("API Call: DeleteContextFile");
    log(`Request: ContextId=${contextId}, FilePath=${filePath}`);
    const req = new $_client.DeleteContextFileRequest({
      authorization: `Bearer ${this.agentBay.getAPIKey()}`,
      contextId,
      filePath,
    });
    const resp = await this.agentBay.getClient().deleteContextFile(req);
    log("Response from DeleteContextFile:", resp.body);
    const requestId = extractRequestId(resp) || "";
    const body = resp.body;
    const success = !!(body && body.success);

    // Check for API-level errors
    const errorMessage = success
      ? ""
      : `[${body?.code || 'Unknown'}] ${body?.message || 'Failed to delete file'}`;

    return {
      requestId,
      success,
      data: success,
      errorMessage,
    };
  }

  /**
   * List files under a specific folder path in a context.
   */
  async listFiles(
    contextId: string,
    parentFolderPath: string,
    pageNumber = 1,
    pageSize = 50
  ): Promise<ContextFileListResult> {
    log("API Call: DescribeContextFiles");
    log(
      `Request: ContextId=${contextId}, ParentFolderPath=${parentFolderPath}, PageNumber=${pageNumber}, PageSize=${pageSize}`
    );
    const req = new $_client.DescribeContextFilesRequest({
      authorization: `Bearer ${this.agentBay.getAPIKey()}`,
      pageNumber,
      pageSize,
      parentFolderPath,
      contextId,
    });
    const resp = await this.agentBay.getClient().describeContextFiles(req);
    log("Response from DescribeContextFiles:", resp.body);
    const requestId = extractRequestId(resp) || "";
    const body = resp.body;

    // Check for API-level errors
    if (body?.success === false && body.code) {
      return {
        requestId,
        success: false,
        entries: [],
        count: undefined,
        errorMessage: `[${body.code}] ${body.message || 'Unknown error'}`,
      };
    }

    const rawList = body?.data || [];
    const entries: ContextFileEntry[] = rawList.map((it: any) => ({
      fileId: it.fileId,
      fileName: it.fileName,
      filePath: it.filePath || "",
      fileType: it.fileType,
      gmtCreate: it.gmtCreate,
      gmtModified: it.gmtModified,
      size: it.size,
      status: it.status,
    }));
    return {
      requestId,
      success: !!(body && body.success),
      entries,
      count: body?.count,
      errorMessage: undefined,
    };
  }
}
