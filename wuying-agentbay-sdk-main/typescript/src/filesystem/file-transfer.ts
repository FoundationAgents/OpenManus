import { AgentBay } from "../agent-bay";
import { Session } from "../session";
import { ContextService } from "../context";
import { FileUrlResult, OperationResult } from "../types/api-response";
import * as fs from "fs";
import * as path from "path";
import fetch from "node-fetch";
import { log } from "../utils/logger";

/**
 * Result structure for file upload operations.
 */
export interface UploadResult {
  /** Whether the upload was successful */
  success: boolean;
  /** Request ID for getting the upload URL */
  requestIdUploadUrl?: string;
  /** Request ID for sync operation */
  requestIdSync?: string;
  /** HTTP status code */
  httpStatus?: number;
  /** ETag of the uploaded file */
  etag?: string;
  /** Number of bytes sent */
  bytesSent: number;
  /** Remote file path */
  path: string;
  /** Error message if upload failed */
  error?: string;
}

/**
 * Result structure for file download operations.
 */
export interface DownloadResult {
  /** Whether the download was successful */
  success: boolean;
  /** Request ID for getting the download URL */
  requestIdDownloadUrl?: string;
  /** Request ID for sync operation */
  requestIdSync?: string;
  /** HTTP status code */
  httpStatus?: number;
  /** Number of bytes received */
  bytesReceived: number;
  /** Remote file path */
  path: string;
  /** Local file path where file was saved */
  localPath: string;
  /** Error message if download failed */
  error?: string;
}

/**
 * FileTransfer provides pre-signed URL upload/download functionality between local and OSS,
 * with integration to Session Context synchronization.
 * 
 * Prerequisites and Constraints:
 * - Session must be associated with the corresponding context_id and path through 
 *   CreateSessionParams.contextSyncs, and remotePath should fall within that 
 *   synchronization path (or conform to backend path rules).
 * - Requires available AgentBay context service (agentBay.context) and session context.
 */
export class FileTransfer {
  private agentBay: AgentBay;
  private contextSvc: ContextService;
  private session: Session;
  private httpTimeout: number;
  private followRedirects: boolean;
  private contextId: string;

  // Task completion states (for compatibility)
  private finishedStates = new Set(["success", "successful", "ok", "finished", "done", "completed", "complete"]);

  /**
   * Initialize FileTransfer with AgentBay client and session.
   * 
   * @param agentBay - AgentBay instance for context service access
   * @param session - Created session object for context operations
   * @param httpTimeout - HTTP request timeout in seconds (default: 60.0)
   * @param followRedirects - Whether to follow HTTP redirects (default: true)
   */
  constructor(
    agentBay: AgentBay,
    session: Session,
    httpTimeout = 60.0,
    followRedirects = true
  ) {
    this.agentBay = agentBay;
    this.contextSvc = agentBay.context;
    this.session = session;
    this.httpTimeout = httpTimeout;
    this.followRedirects = followRedirects;
    this.contextId = session.fileTransferContextId || "";
  }

  /**
   * Upload workflow:
   * 1) Get OSS pre-signed URL via context.getFileUploadUrl
   * 2) Upload local file to OSS using the URL (HTTP PUT)
   * 3) Trigger session.context.sync(mode="download") to sync OSS objects to cloud disk
   * 4) If wait=true, poll session.context.info until upload task reaches completion or timeout
   *
   * Returns UploadResult containing request_ids, HTTP status, ETag and other information.
   */
  async upload(
    localPath: string,
    remotePath: string,
    options?: {
      contentType?: string;
      wait?: boolean;
      waitTimeout?: number;
      pollInterval?: number;
      progressCb?: (bytesTransferred: number) => void;
    }
  ): Promise<UploadResult> {
    const {
      contentType = null,
      wait = true,
      waitTimeout = 30.0,
      pollInterval = 1.5,
      progressCb = undefined
    } = options || {};

    try {
      // 0. Parameter validation
      if (!fs.existsSync(localPath)) {
        return {
          success: false,
          bytesSent: 0,
          path: remotePath,
          error: `Local file not found: ${localPath}`
        };
      }

      if (!this.contextId) {
        return {
          success: false,
          bytesSent: 0,
          path: remotePath,
          error: "No context ID"
        };
      }

      // 1. Get pre-signed upload URL
      const urlRes = await this.contextSvc.getFileUploadUrl(this.contextId, remotePath);
      if (!urlRes.success || !urlRes.url) {
        return {
          success: false,
          requestIdUploadUrl: urlRes.requestId,
          bytesSent: 0,
          path: remotePath,
          error: `getFileUploadUrl failed: ${urlRes.url || "unknown error"}`
        };
      }

      const uploadUrl = urlRes.url;
      const reqIdUpload = urlRes.requestId;

      log(`Uploading ${localPath} to ${uploadUrl}`);

      // 2. PUT upload to pre-signed URL
      try {
        const { httpStatus, etag, bytesSent } = await this.putFile(
          uploadUrl,
          localPath,
          contentType,
          progressCb
        );
        
        log(`Upload completed with HTTP ${httpStatus}`);
        if (httpStatus && ![200, 201, 204].includes(httpStatus)) {
          return {
            success: false,
            requestIdUploadUrl: reqIdUpload,
            httpStatus,
            etag,
            bytesSent,
            path: remotePath,
            error: `Upload failed with HTTP ${httpStatus}`
          };
        }
      } catch (e: any) {
        return {
          success: false,
          requestIdUploadUrl: reqIdUpload,
          bytesSent: 0,
          path: remotePath,
          error: `Upload exception: ${e.message || e}`
        };
      }

      // 3. Trigger sync to cloud disk (download mode), download from oss to cloud disk
      let reqIdSync: string | undefined;
      try {
        log("Triggering sync to cloud disk");
        reqIdSync = await this.awaitSync("download", remotePath, this.contextId);
      } catch (e: any) {
        return {
          success: false,
          requestIdUploadUrl: reqIdUpload,
          requestIdSync: reqIdSync,
          httpStatus: 200, // Assuming previous step succeeded
          etag: "", // Assuming previous step succeeded
          bytesSent: fs.statSync(localPath).size, // Assuming previous step succeeded
          path: remotePath,
          error: `session.context.sync(upload) failed: ${e.message || e}`
        };
      }

      log(`Sync request ID: ${reqIdSync}`);
      
      // 4. Optionally wait for task completion
      if (wait) {
        const { success, error } = await this.waitForTask({
          contextId: this.contextId,
          remotePath,
          taskType: "download",
          timeout: waitTimeout,
          interval: pollInterval
        });
        
        if (!success) {
          return {
            success: false,
            requestIdUploadUrl: reqIdUpload,
            requestIdSync: reqIdSync,
            httpStatus: 200, // Assuming previous step succeeded
            etag: "", // Assuming previous step succeeded
            bytesSent: fs.statSync(localPath).size, // Assuming previous step succeeded
            path: remotePath,
            error: `Upload sync not finished: ${error || "timeout or unknown"}`
          };
        }
      }

      return {
        success: true,
        requestIdUploadUrl: reqIdUpload,
        requestIdSync: reqIdSync,
        httpStatus: 200,
        etag: "",
        bytesSent: fs.statSync(localPath).size,
        path: remotePath
      };
    } catch (e: any) {
      return {
        success: false,
        bytesSent: 0,
        path: remotePath,
        error: `Upload failed: ${e.message || e}`
      };
    }
  }

  /**
   * Download workflow:
   * 1) Trigger session.context.sync(mode="upload") to sync cloud disk data to OSS
   * 2) Get pre-signed download URL via context.getFileDownloadUrl
   * 3) Download the file and save to local localPath
   * 4) If wait=true, wait for download task to reach completion after step 1 
   *    (ensuring backend has prepared the download object)
   *
   * Returns DownloadResult containing sync and download request_ids, HTTP status, byte count, etc.
   */
  async download(
    remotePath: string,
    localPath: string,
    options?: {
      overwrite?: boolean;
      wait?: boolean;
      waitTimeout?: number;
      pollInterval?: number;
      progressCb?: (bytesReceived: number) => void;
    }
  ): Promise<DownloadResult> {
    const {
      overwrite = true,
      wait = true,
      waitTimeout = 30.0,
      pollInterval = 1.5,
      progressCb = undefined
    } = options || {};

    try {
      // Use default context if none provided
      if (!this.contextId) {
        return {
          success: false,
          bytesReceived: 0,
          path: remotePath,
          localPath,
          error: "No context ID"
        };
      }

      // 1. Trigger cloud disk to OSS download sync
      let reqIdSync: string | undefined;
      try {
        reqIdSync = await this.awaitSync("upload", remotePath, this.contextId);
      } catch (e: any) {
        return {
          success: false,
          requestIdSync: reqIdSync,
          bytesReceived: 0,
          path: remotePath,
          localPath,
          error: `session.context.sync(download) failed: ${e.message || e}`
        };
      }

      // Optionally wait for task completion (ensure object is ready in OSS)
      if (wait) {
        const { success, error } = await this.waitForTask({
          contextId: this.contextId,
          remotePath,
          taskType: "upload",
          timeout: waitTimeout,
          interval: pollInterval
        });
        
        if (!success) {
          return {
            success: false,
            requestIdSync: reqIdSync,
            bytesReceived: 0,
            path: remotePath,
            localPath,
            error: `Download sync not finished: ${error || "timeout or unknown"}`
          };
        }
      }

      // 2. Get pre-signed download URL
      const urlRes = await this.contextSvc.getFileDownloadUrl(this.contextId, remotePath);
      if (!urlRes.success || !urlRes.url) {
        return {
          success: false,
          requestIdDownloadUrl: urlRes.requestId,
          requestIdSync: reqIdSync,
          bytesReceived: 0,
          path: remotePath,
          localPath,
          error: `getFileDownloadUrl failed: ${urlRes.url || "unknown error"}`
        };
      }

      const downloadUrl = urlRes.url;
      const reqIdDownload = urlRes.requestId;

      // 3. Download and save to local
      try {
        // Ensure directory exists
        const dir = path.dirname(localPath);
        if (!fs.existsSync(dir)) {
          fs.mkdirSync(dir, { recursive: true });
        }

        if (fs.existsSync(localPath) && !overwrite) {
          return {
            success: false,
            requestIdDownloadUrl: reqIdDownload,
            requestIdSync: reqIdSync,
            bytesReceived: 0,
            path: remotePath,
            localPath,
            error: `Destination exists and overwrite=false: ${localPath}`
          };
        }

        const bytesReceived = await this.getFile(
          downloadUrl,
          localPath,
          progressCb
        );

        if (fs.existsSync(localPath)) {
          return {
            success: true,
            requestIdDownloadUrl: reqIdDownload,
            requestIdSync: reqIdSync,
            httpStatus: 200,
            bytesReceived: fs.statSync(localPath).size,
            path: remotePath,
            localPath
          };
        } else {
          return {
            success: false,
            requestIdDownloadUrl: reqIdDownload,
            requestIdSync: reqIdSync,
            bytesReceived,
            path: remotePath,
            localPath,
            error: "Download completed but file not found"
          };
        }
      } catch (e: any) {
        return {
          success: false,
          requestIdDownloadUrl: reqIdDownload,
          requestIdSync: reqIdSync,
          bytesReceived: 0,
          path: remotePath,
          localPath,
          error: `Download exception: ${e.message || e}`
        };
      }
    } catch (e: any) {
      return {
        success: false,
        bytesReceived: 0,
        path: remotePath,
        localPath,
        error: `Download failed: ${e.message || e}`
      };
    }
  }

  // ========== Internal Utilities ==========

  /**
   * Compatibility wrapper for session.context.sync which may be sync or async:
   * - Try async call first
   * - Fall back to sync call
   * Returns request_id if available
   */
  private async awaitSync(mode: string, remotePath = "", contextId = ""): Promise<string | undefined> {
    mode = mode.toLowerCase().trim();

    // Check if session has context property
    if (!this.session.context) {
      throw new Error("Session does not have context property");
    }

    const syncFn = this.session.context.sync.bind(this.session.context);
    log(`session.context.sync(mode=${mode}, path=${remotePath}, contextId=${contextId})`);
    
    // Try calling with all parameters
    try {
      const result = await syncFn(contextId || undefined, remotePath || undefined, mode);
      log(`   Result: ${result.success}`);
      return result.requestId;
    } catch (e1) {
      // Backend may not support all parameters, try with mode and path only
      try {
        const result = await syncFn(undefined, remotePath || undefined, mode);
        log(`   Result: ${result.success}`);
        return result.requestId;
      } catch (e2) {
        // Backend may not support mode or path parameter
        try {
          const result = await syncFn(undefined, undefined, mode);
          log(`   Result: ${result.success}`);
          return result.requestId;
        } catch (e3) {
          // Backend may not support mode parameter
          const result = await syncFn();
          log(`   Result: ${result.success}`);
          return result.requestId;
        }
      }
    }
  }

  /**
   * Poll session.context.info within timeout to check if specified task is completed.
   * Returns { success, error } object.
   */
  private async waitForTask(options: {
    contextId: string;
    remotePath: string;
    taskType?: string;
    timeout: number;
    interval: number;
  }): Promise<{ success: boolean; error?: string }> {
    const { contextId, remotePath, taskType, timeout, interval } = options;
    const deadline = Date.now() + timeout * 1000;
    let lastErr: string | null = null;

    while (Date.now() < deadline) {
      try {
        // Check if session has context property
        if (!this.session.context) {
          throw new Error("Session does not have context property");
        }

        const infoFn = this.session.context.infoWithParams.bind(this.session.context);
        // Try calling with filter parameters
        let res;
        try {
          res = await infoFn(contextId, remotePath, taskType);
        } catch (e1) {
          try {
            res = await infoFn();
          } catch (e2) {
            // If all attempts fail, re-throw the last error
            throw e2;
          }
        }

        // Parse response
        const statusList = res.contextStatusData || [];
        for (const item of statusList) {
          const cid = item.contextId;
          const path = item.path;
          const ttype = item.taskType;
          const status = item.status;
          const err = item.errorMessage;

          if (cid === contextId && path === remotePath && (taskType === undefined || ttype === taskType)) {
            if (err) {
              return { success: false, error: `Task error: ${err}` };
            }
            if (status && this.finishedStates.has(status.toLowerCase())) {
              return { success: true };
            }
            // Otherwise continue waiting
          }
        }
        lastErr = "task not finished";
      } catch (e: any) {
        lastErr = `info error: ${e.message || e}`;
      }

      // Wait before next poll
      await new Promise(resolve => setTimeout(resolve, interval * 1000));
    }

    return { success: false, error: lastErr || "timeout" };
  }

  /**
   * Synchronously PUT file using node-fetch.
   * Returns { status, etag, bytesSent }
   */
  private async putFile(
    url: string,
    filePath: string,
    contentType: string | null,
    progressCb?: (bytesTransferred: number) => void
  ): Promise<{ httpStatus: number; etag?: string; bytesSent: number }> {
    const headers: Record<string, string> = {};
    if (contentType) {
      headers["Content-Type"] = contentType;
    }

    const fileBuffer = fs.readFileSync(filePath);
    const response = await fetch(url, {
      method: "PUT",
      body: fileBuffer,
      headers
    });

    const status = response.status;
    const etag = response.headers.get("ETag") || undefined;
    const bytesSent = fileBuffer.length;

    if (progressCb) {
      progressCb(bytesSent);
    }

    return { httpStatus: status, etag, bytesSent };
  }

  /**
   * Synchronously GET download to local file using node-fetch.
   * Returns bytesReceived
   */
  private async getFile(
    url: string,
    destPath: string,
    progressCb?: (bytesReceived: number) => void
  ): Promise<number> {
    let bytesReceived = 0;
    
    const response = await fetch(url);
    const status = response.status;
    
    if (status !== 200) {
      throw new Error(`HTTP ${status}`);
    }

    const buffer = await response.buffer();
    bytesReceived = buffer.length;
    
    // Save to file
    fs.writeFileSync(destPath, buffer);
    
    if (progressCb) {
      progressCb(bytesReceived);
    }

    return bytesReceived;
  }
}