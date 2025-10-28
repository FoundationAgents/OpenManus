import { Session } from "../session";
import {
  OSSClientResult,
  OSSUploadResult,
  OSSDownloadResult,
} from "../types/api-response";


/**
 * Handles OSS operations in the AgentBay cloud environment.
 */
export class Oss {
  private session: Session;

  /**
   * Initialize an Oss object.
   *
   * @param session - The Session instance that this Oss belongs to.
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
   * Initialize OSS environment variables with the specified credentials.
   * Corresponds to Python's env_init() method
   *
   * @param accessKeyId - The access key ID
   * @param accessKeySecret - The access key secret
   * @param securityToken - The security token (optional)
   * @param endpoint - The OSS endpoint (optional)
   * @param region - The OSS region (optional)
   * @returns OSSClientResult with client configuration and requestId
   * @throws APIError if the operation fails.
   */
  async envInit(
    accessKeyId: string,
    accessKeySecret: string,
    securityToken?: string,
    endpoint?: string,
    region?: string
  ): Promise<OSSClientResult> {
    try {
      const args = {
        access_key_id: accessKeyId,
        access_key_secret: accessKeySecret,
        security_token: securityToken || "",
        endpoint: endpoint || "",
        region: region || "",
      };
      const result = await this.session.callMcpTool("oss_env_init", args);

      if (!result.success) {
        return {
          requestId: result.requestId,
          success: false,
          clientConfig: {},
          errorMessage: result.errorMessage,
        };
      }

      let clientConfig: Record<string, any> = {};
      try {
        clientConfig = JSON.parse(result.data);
      } catch (err) {
        return {
          requestId: result.requestId,
          success: false,
          clientConfig: {},
          errorMessage: `Failed to parse client config: ${err}`,
        };
      }

      return {
        requestId: result.requestId,
        success: true,
        clientConfig,
        errorMessage: "",
      };
    } catch (error) {
      return {
        requestId: "",
        success: false,
        clientConfig: {},
        errorMessage: `Failed to initialize OSS environment: ${error}`,
      };
    }
  }

  /**
   * Upload a file to OSS.
   * Corresponds to Python's upload() method
   *
   * @param bucket - The OSS bucket name
   * @param object - The OSS object key
   * @param path - The local file path to upload
   * @returns OSSUploadResult with upload result and requestId
   * @throws APIError if the operation fails.
   */
  async upload(
    bucket: string,
    object: string,
    path: string
  ): Promise<OSSUploadResult> {
    try {
      const args = {
        bucket,
        object,
        path,
      };
      const result = await this.session.callMcpTool("oss_upload", args);

      return {
        requestId: result.requestId,
        success: result.success,
        content: result.data,
        errorMessage: result.errorMessage,
      };
    } catch (error) {
      return {
        requestId: "",
        success: false,
        content: "",
        errorMessage: `Failed to upload file: ${error}`,
      };
    }
  }

  /**
   * Upload a file to OSS using an anonymous URL.
   * Corresponds to Python's upload_anonymous() method
   *
   * @param url - The anonymous upload URL
   * @param path - The local file path to upload
   * @returns OSSUploadResult with upload result and requestId
   * @throws APIError if the operation fails.
   */
  async uploadAnonymous(url: string, path: string): Promise<OSSUploadResult> {
    try {
      const args = {
        url,
        path,
      };
      const result = await this.session.callMcpTool("oss_upload_annon", args);

      return {
        requestId: result.requestId,
        success: result.success,
        content: result.data,
        errorMessage: result.errorMessage,
      };
    } catch (error) {
      return {
        requestId: "",
        success: false,
        content: "",
        errorMessage: `Failed to upload file anonymously: ${error}`,
      };
    }
  }

  /**
   * Download a file from OSS.
   * Corresponds to Python's download() method
   *
   * @param bucket - The OSS bucket name
   * @param object - The OSS object key
   * @param path - The local file path to save the downloaded file
   * @returns OSSDownloadResult with download result and requestId
   * @throws APIError if the operation fails.
   */
  async download(
    bucket: string,
    object: string,
    path: string
  ): Promise<OSSDownloadResult> {
    try {
      const args = {
        bucket,
        object,
        path,
      };
      const result = await this.session.callMcpTool("oss_download", args);

      return {
        requestId: result.requestId,
        success: result.success,
        content: result.data,
        errorMessage: result.errorMessage,
      };
    } catch (error) {
      return {
        requestId: "",
        success: false,
        content: "",
        errorMessage: `Failed to download file: ${error}`,
      };
    }
  }

  /**
   * Download a file from OSS using an anonymous URL.
   * Corresponds to Python's download_anonymous() method
   *
   * @param url - The anonymous download URL
   * @param path - The local file path to save the downloaded file
   * @returns OSSDownloadResult with download result and requestId
   * @throws APIError if the operation fails.
   */
  async downloadAnonymous(
    url: string,
    path: string
  ): Promise<OSSDownloadResult> {
    try {
      const args = {
        url,
        path,
      };
      const result = await this.session.callMcpTool("oss_download_annon", args);

      return {
        requestId: result.requestId,
        success: result.success,
        content: result.data,
        errorMessage: result.errorMessage,
      };
    } catch (error) {
      return {
        requestId: "",
        success: false,
        content: "",
        errorMessage: `Failed to download file anonymously: ${error}`,
      };
    }
  }
}
