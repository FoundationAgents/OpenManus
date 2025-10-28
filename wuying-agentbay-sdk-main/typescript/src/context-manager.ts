import { Client } from "./api/client";
import { GetContextInfoRequest, SyncContextRequest } from "./api/models/model";
import { ApiResponse, extractRequestId } from "./types/api-response";
import { log, logError } from "./utils/logger";

export interface ContextStatusData {
  contextId: string;
  path: string;
  errorMessage: string;
  status: string;
  startTime: number;
  finishTime: number;
  taskType: string;
}

export interface ContextStatusItem {
  type: string;
  data: string;
}

export interface ContextInfoResult extends ApiResponse {
  success?: boolean;
  contextStatusData: ContextStatusData[];
  errorMessage?: string;
}

export interface ContextSyncResult extends ApiResponse {
  success: boolean;
  errorMessage?: string;
}

export type SyncCallback = (success: boolean) => void;

export interface SessionInterface {
  getAPIKey(): string;
  getClient(): Client;
  getSessionId(): string;
}

export class ContextManager {
  private session: SessionInterface;

  constructor(session: SessionInterface) {
    this.session = session;
  }

  async info(): Promise<ContextInfoResult> {
    return this.infoWithParams();
  }

  async infoWithParams(
    contextId?: string,
    path?: string,
    taskType?: string
  ): Promise<ContextInfoResult> {
    const request = new GetContextInfoRequest({
      authorization: `Bearer ${this.session.getAPIKey()}`,
      sessionId: this.session.getSessionId(),
    });

    // Set optional parameters if provided
    if (contextId) {
      request.contextId = contextId;
    }
    if (path) {
      request.path = path;
    }
    if (taskType) {
      request.taskType = taskType;
    }

    // Log API request (matching Go version format)
    log("API Call: GetContextInfo");
    let requestLog = `Request: SessionId=${request.sessionId}`;
    if (request.contextId) {
      requestLog += `, ContextId=${request.contextId}`;
    }
    if (request.path) {
      requestLog += `, Path=${request.path}`;
    }
    if (request.taskType) {
      requestLog += `, TaskType=${request.taskType}`;
    }
    log(requestLog);

    try {
      const response = await this.session.getClient().getContextInfo(request);

      // Extract RequestID
      const requestId = extractRequestId(response) || "";

      if (response?.body) {
        log("Response from GetContextInfo:", response.body);
      }

      // Check for API-level errors
      if (response?.body?.success === false && response.body.code) {
        return {
          requestId,
          success: false,
          contextStatusData: [],
          errorMessage: `[${response.body.code}] ${response.body.message || 'Unknown error'}`,
        };
      }

      // Parse the context status data
      const contextStatusData: ContextStatusData[] = [];
      if (response?.body?.data?.contextStatus) {
        try {
          // First, parse the outer array
          const contextStatusStr = response.body.data.contextStatus;
          const statusItems: ContextStatusItem[] = JSON.parse(contextStatusStr);
          
          // Process each item in the array
          for (const item of statusItems) {
            if (item.type === "data") {
              // Parse the inner data string
              const dataItems: ContextStatusData[] = JSON.parse(item.data);
              contextStatusData.push(...dataItems);
            }
          }
        } catch (error) {
          logError("Error parsing context status:", error);
        }
      }

      return {
        requestId,
        success: true,
        contextStatusData,
        errorMessage: undefined,
      };
    } catch (error) {
      logError("Error calling GetContextInfo:", error);
      throw new Error(`Failed to get context info: ${error}`);
    }
  }

  async sync(
    contextId?: string,
    path?: string,
    mode?: string,
    callback?: SyncCallback,
    maxRetries: number = 150,
    retryInterval: number = 1500
  ): Promise<ContextSyncResult> {
    const request = new SyncContextRequest({
      authorization: `Bearer ${this.session.getAPIKey()}`,
      sessionId: this.session.getSessionId(),
    });

    // Set optional parameters if provided
    if (contextId) {
      request.contextId = contextId;
    }
    if (path) {
      request.path = path;
    }
    if (mode) {
      request.mode = mode;
    }

    // Log API request (matching Go version format)
    log("API Call: SyncContext");
    let requestLog = `Request: SessionId=${request.sessionId}`;
    if (request.contextId) {
      requestLog += `, ContextId=${request.contextId}`;
    }
    if (request.path) {
      requestLog += `, Path=${request.path}`;
    }
    if (request.mode) {
      requestLog += `, Mode=${request.mode}`;
    }
    log(requestLog);

    try {
      const response = await this.session.getClient().syncContext(request);

      // Extract RequestID
      const requestId = extractRequestId(response) || "";

      if (response?.body) {
        log("Response from SyncContext:", response.body);
      }

      // Check for API-level errors
      if (response?.body?.success === false && response.body.code) {
        return {
          requestId,
          success: false,
          errorMessage: `[${response.body.code}] ${response.body.message || 'Unknown error'}`,
        };
      }

      let success = false;
      if (response?.body?.success !== undefined) {
        success = response.body.success;
      }

      // If callback is provided, start polling in background (async mode)
      if (callback && success) {
        // Start polling in background without blocking
        this.pollForCompletion(callback, contextId, path, maxRetries, retryInterval)
          .catch((error) => {
            logError("Error in background polling:", error);
            callback(false);
          });
        return {
          requestId,
          success,
        };
      }

      // If no callback, wait for completion (sync mode)
      if (success) {
        const finalSuccess = await this.pollForCompletionAsync(
          contextId,
          path,
          maxRetries,
          retryInterval
        );
        return {
          requestId,
          success: finalSuccess,
        };
      }

      return {
        requestId,
        success,
      };
    } catch (error) {
      logError("Error calling SyncContext:", error);
      throw new Error(`Failed to sync context: ${error}`);
    }
  }

  /**
   * Polls the info interface to check if sync is completed and calls callback.
   */
  private async pollForCompletion(
    callback: SyncCallback,
    contextId?: string,
    path?: string,
    maxRetries: number = 150,
    retryInterval: number = 1500
  ): Promise<void> {
    for (let retry = 0; retry < maxRetries; retry++) {
      try {
        // Get context status data
        const infoResult = await this.infoWithParams(contextId, path);

        // Check if all sync tasks are completed
        let allCompleted = true;
        let hasFailure = false;
        let hasSyncTasks = false;

        for (const item of infoResult.contextStatusData) {
          // We only care about sync tasks (upload/download)
          if (item.taskType !== "upload" && item.taskType !== "download") {
            continue;
          }

          hasSyncTasks = true;
          log(`Sync task ${item.contextId} status: ${item.status}, path: ${item.path}`);

          if (item.status !== "Success" && item.status !== "Failed") {
            allCompleted = false;
            break;
          }

          if (item.status === "Failed") {
            hasFailure = true;
            logError(`Sync failed for context ${item.contextId}: ${item.errorMessage}`);
          }
        }

        if (allCompleted || !hasSyncTasks) {
          // All tasks completed or no sync tasks found
          if (hasFailure) {
            log("Context sync completed with failures");
            callback(false);
          } else if (hasSyncTasks) {
            log("Context sync completed successfully");
            callback(true);
          } else {
            log("No sync tasks found");
            callback(true);
          }
          return; // Exit the function immediately after calling callback
        }

        log(`Waiting for context sync to complete, attempt ${retry + 1}/${maxRetries}`);
        await this.sleep(retryInterval);
      } catch (error) {
        logError(`Error checking context status on attempt ${retry + 1}:`, error);
        await this.sleep(retryInterval);
      }
    }

    // If we've exhausted all retries, call callback with failure
    logError(`Context sync polling timed out after ${maxRetries} attempts`);
    callback(false);
  }

  /**
   * Async version of polling for sync completion.
   */
  private async pollForCompletionAsync(
    contextId?: string,
    path?: string,
    maxRetries: number = 150,
    retryInterval: number = 1500
  ): Promise<boolean> {
    for (let retry = 0; retry < maxRetries; retry++) {
      try {
        // Get context status data
        const infoResult = await this.infoWithParams(contextId, path);

        // Check if all sync tasks are completed
        let allCompleted = true;
        let hasFailure = false;
        let hasSyncTasks = false;

        for (const item of infoResult.contextStatusData) {
          // We only care about sync tasks (upload/download)
          if (item.taskType !== "upload" && item.taskType !== "download") {
            continue;
          }

          hasSyncTasks = true;
          log(`Sync task ${item.contextId} status: ${item.status}, path: ${item.path}`);

          if (item.status !== "Success" && item.status !== "Failed") {
            allCompleted = false;
            break;
          }

          if (item.status === "Failed") {
            hasFailure = true;
            logError(`Sync failed for context ${item.contextId}: ${item.errorMessage}`);
          }
        }

        if (allCompleted || !hasSyncTasks) {
          // All tasks completed or no sync tasks found
          if (hasFailure) {
            log("Context sync completed with failures");
            return false;
          } else if (hasSyncTasks) {
            log("Context sync completed successfully");
            return true;
          } else {
            log("No sync tasks found");
            return true;
          }
        }

        log(`Waiting for context sync to complete, attempt ${retry + 1}/${maxRetries}`);
        await this.sleep(retryInterval);
      } catch (error) {
        logError(`Error checking context status on attempt ${retry + 1}:`, error);
        await this.sleep(retryInterval);
      }
    }

    // If we've exhausted all retries, return failure
    logError(`Context sync polling timed out after ${maxRetries} attempts`);
    return false;
  }

  /**
   * Sleep utility function for TypeScript
   */
  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
}

export function newContextManager(session: SessionInterface): ContextManager {
  return new ContextManager(session);
}
