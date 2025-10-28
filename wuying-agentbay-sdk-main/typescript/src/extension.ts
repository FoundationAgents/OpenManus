import * as fs from "fs";
import * as path from "path";
import * as crypto from "crypto";
import fetch from "node-fetch";
import { AgentBay } from "./agent-bay";
import { ContextService, Context } from "./context";
import { AgentBayError } from "./exceptions";
import { OperationResult, ContextFileListResult, FileUrlResult } from "./types/api-response";
import { log, logError } from "./utils/logger";

// ==============================================================================
// Constants
// ==============================================================================
const EXTENSIONS_BASE_PATH = "/tmp/extensions";

// ==============================================================================
// 1. Data Models
// ==============================================================================

/**
 * Represents a browser extension as a cloud resource.
 */
export class Extension {
  /**
   * The unique identifier of the extension.
   */
  id: string;

  /**
   * The name of the extension.
   */
  name: string;

  /**
   * Date and time when the extension was created.
   */
  createdAt?: string;

  /**
   * Initialize an Extension object.
   *
   * @param id - The unique identifier of the extension.
   * @param name - The name of the extension.
   * @param createdAt - Date and time when the extension was created.
   */
  constructor(id: string, name: string, createdAt?: string) {
    this.id = id;
    this.name = name;
    this.createdAt = createdAt;
  }
}

/**
 * Configuration options for browser extension integration.
 * 
 * This class encapsulates the necessary parameters for setting up
 * browser extension synchronization and context management.
 */
export class ExtensionOption {
  /**
   * ID of the extension context for browser extensions.
   */
  contextId: string;

  /**
   * List of extension IDs to be loaded/synchronized.
   */
  extensionIds: string[];

  /**
   * Initialize ExtensionOption with context and extension configuration.
   * 
   * @param contextId - ID of the extension context for browser extensions.
   *                   This should match the context where extensions are stored.
   * @param extensionIds - List of extension IDs to be loaded in the browser session.
   *                      Each ID should correspond to a valid extension in the context.
   * 
   * @throws {Error} If contextId is empty or extensionIds is empty.
   */
  constructor(contextId: string, extensionIds: string[]) {
    if (!contextId || !contextId.trim()) {
      throw new Error("contextId cannot be empty");
    }

    if (!extensionIds || extensionIds.length === 0) {
      throw new Error("extensionIds cannot be empty");
    }

    this.contextId = contextId;
    this.extensionIds = extensionIds;
  }

  /**
   * String representation of ExtensionOption.
   */
  toString(): string {
    return `ExtensionOption(contextId='${this.contextId}', extensionIds=${JSON.stringify(this.extensionIds)})`;
  }

  /**
   * Human-readable string representation.
   */
  toDisplayString(): string {
    return `Extension Config: ${this.extensionIds.length} extension(s) in context '${this.contextId}'`;
  }

  /**
   * Validate the extension option configuration.
   * 
   * @returns True if configuration is valid, false otherwise.
   */
  validate(): boolean {
    try {
      // Check contextId
      if (!this.contextId || !this.contextId.trim()) {
        return false;
      }

      // Check extensionIds
      if (!this.extensionIds || this.extensionIds.length === 0) {
        return false;
      }

      // Check that all extension IDs are non-empty strings
      for (const extId of this.extensionIds) {
        if (typeof extId !== 'string' || !extId.trim()) {
          return false;
        }
      }

      return true;
    } catch (error) {
      return false;
    }
  }
}

// ==============================================================================
// 2. Core Service Class (Scoped Stateless Model)
// ==============================================================================

/**
 * Provides methods to manage user browser extensions.
 * This service integrates with the existing context functionality for file operations.
 * 
 * **Usage** (Simplified - Auto-detection):
 * ```typescript
 * // Service automatically detects if context exists and creates if needed
 * const extensionsService = new ExtensionsService(agentBay, "browser_extensions");
 * 
 * // Or use with empty contextId to auto-generate context name
 * const extensionsService = new ExtensionsService(agentBay);  // Uses default generated name
 * 
 * // Use the service immediately - initialization happens automatically
 * const extension = await extensionsService.create("/path/to/plugin.zip");
 * ```
 * 
 * **Integration with ExtensionOption (Simplified)**:
 * ```typescript
 * // Create extensions and configure for browser sessions
 * const extensionsService = new ExtensionsService(agentBay, "my_extensions");
 * const ext1 = await extensionsService.create("/path/to/ext1.zip");
 * const ext2 = await extensionsService.create("/path/to/ext2.zip");
 * 
 * // Create extension option for browser integration (no contextId needed!)
 * const extOption = extensionsService.createExtensionOption([ext1.id, ext2.id]);
 * 
 * // Use with BrowserContext for session creation
 * const browserContext = new BrowserContext({
 *   contextId: "browser_session",
 *   autoUpload: true,
 *   extensionOption: extOption  // All extension config encapsulated
 * });
 * ```
 * 
 * **Context Management**:
 * - If contextId provided and exists: Uses the existing context
 * - If contextId provided but doesn't exist: Creates context with provided name
 * - If contextId empty or not provided: Generates default name and creates context
 * - No need to manually manage context creation or call initialize()
 * - Context initialization happens automatically on first method call
 */
export class ExtensionsService {
  private agentBay: AgentBay;
  private contextService: ContextService;
  private extensionContext!: Context;
  private contextId!: string;
  private contextName: string;
  private autoCreated: boolean;
  private _initializationPromise: Promise<void> | null = null;

  /**
   * Initializes the ExtensionsService with a context.
   *
   * @param agentBay - The AgentBay client instance.
   * @param contextId - The context ID or name. If empty or not provided,
   *                   a default context name will be generated automatically.
   *                   If the context doesn't exist, it will be automatically created.
   *                   
   * Note:
   *   The service automatically detects if the context exists. If not,
   *   it creates a new context with the provided name or a generated default name.
   *   Context initialization is handled lazily on first use.
   */
  constructor(agentBay: AgentBay, contextId: string = "") {
    if (!agentBay) {
      throw new AgentBayError("AgentBay instance is required");
    }
    if (!agentBay.context) {
      throw new AgentBayError("AgentBay instance must have a context service");
    }
    
    this.agentBay = agentBay;
    this.contextService = agentBay.context;
    this.autoCreated = true;

    // Generate default context name if contextId is empty
    if (!contextId || contextId.trim() === "") {
      contextId = `extensions-${Math.floor(Date.now() / 1000)}`;
      log(`Generated default context name: ${contextId}`);
    }

    this.contextName = contextId;
    
    // Initialize context lazily - will be set on first method call
    this._initializationPromise = this._initializeContext();
  }

  /**
   * Internal method to initialize the context.
   * This ensures the context is ready before any operations.
   */
  private async _initializeContext(): Promise<void> {
    try {
      // Context doesn't exist, create it
      const contextResult = await this.contextService.get(this.contextName, true);
      if (!contextResult.success || !contextResult.context) {
        throw new AgentBayError(`Failed to create extension repository context: ${this.contextName}`);
      }

      this.extensionContext = contextResult.context;
      this.contextId = this.extensionContext.id;
    } catch (error) {
      throw new AgentBayError(`Failed to initialize ExtensionsService: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  /**
   * Ensures the service is initialized before performing operations.
   */
  private async _ensureInitialized(): Promise<void> {
    if (this._initializationPromise) {
      await this._initializationPromise;
      this._initializationPromise = null;
    }
  }

  /**
   * An internal helper method that encapsulates the flow of "get upload URL for a specific path and upload".
   * Uses the existing context service for file operations.
   *
   * @param localPath - The path to the local file.
   * @param remotePath - The path of the file in context storage.
   * 
   * @throws {AgentBayError} If getting the credential or uploading fails.
   */
  private async _uploadToCloud(localPath: string, remotePath: string): Promise<void> {
    try {
      // 1. Get upload URL using context service
      const urlResult = await this.contextService.getFileUploadUrl(this.contextId, remotePath);
      if (!urlResult.success || !urlResult.url) {
        throw new AgentBayError(`Failed to get upload URL: ${urlResult.url || 'No URL returned'}`);
      }

      const preSignedUrl = urlResult.url;

      // 2. Use the presigned URL to upload the file directly
      const fileBuffer = fs.readFileSync(localPath);
      
      const response = await fetch(preSignedUrl, {
        method: 'PUT',
        body: fileBuffer,
      });

      if (!response.ok) {
        throw new AgentBayError(`HTTP error uploading file: ${response.status} ${response.statusText}`);
      }
    } catch (error) {
      if (error instanceof AgentBayError) {
        throw error;
      }
      throw new AgentBayError(`An error occurred while uploading the file: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  /**
   * Lists all available browser extensions within this context from the cloud.
   * Uses the context service to list files under the extensions directory.
   * 
   * @returns Promise that resolves to an array of Extension objects.
   * @throws {AgentBayError} If listing extensions fails.
   */
  async list(): Promise<Extension[]> {
    await this._ensureInitialized();
    
    try {
      // Use context service to list files in the extensions directory
      const fileListResult = await this.contextService.listFiles(
        this.contextId,
        EXTENSIONS_BASE_PATH,
        1, // pageNumber
        100 // pageSize - reasonable limit for extensions
      );

      if (!fileListResult.success) {
        throw new AgentBayError("Failed to list extensions: Context file listing failed.");
      }

      const extensions: Extension[] = [];
      for (const fileEntry of fileListResult.entries) {
        // Extract the extension ID from the file name
        const extensionId = fileEntry.fileName || fileEntry.filePath;
        extensions.push(new Extension(
          extensionId,
          fileEntry.fileName || extensionId,
          fileEntry.gmtCreate
        ));
      }
      return extensions;
    } catch (error) {
      if (error instanceof AgentBayError) {
        throw error;
      }
      throw new AgentBayError(`An error occurred while listing browser extensions: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  /**
   * Uploads a new browser extension from a local path into the current context.
   * 
   * @param localPath - Path to the local extension file (must be a .zip file).
   * @returns Promise that resolves to an Extension object.
   * @throws {Error} If the local file doesn't exist.
   * @throws {Error} If the file format is not supported (only .zip is supported).
   * @throws {AgentBayError} If upload fails.
   */
  async create(localPath: string): Promise<Extension> {
    await this._ensureInitialized();
    
    if (!fs.existsSync(localPath)) {
      throw new Error(`The specified local file was not found: ${localPath}`);
    }

    // Determine the ID and cloud path before uploading
    // Validate file type - only ZIP format is supported
    const fileExtension = path.extname(localPath).toLowerCase();
    if (fileExtension !== '.zip') {
      throw new Error(`Unsupported plugin format '${fileExtension}'. Only ZIP format (.zip) is supported.`);
    }

    const extensionId = `ext_${crypto.randomBytes(16).toString('hex')}${fileExtension}`;
    const extensionName = path.basename(localPath);
    const remotePath = `${EXTENSIONS_BASE_PATH}/${extensionId}`;

    // Use the helper method to perform the cloud upload
    await this._uploadToCloud(localPath, remotePath);

    // Upload implies creation. Return a locally constructed object with basic info.
    return new Extension(extensionId, extensionName);
  }

  /**
   * Updates an existing browser extension in the current context with a new file.
   * 
   * @param extensionId - ID of the extension to update.
   * @param newLocalPath - Path to the new local extension file.
   * @returns Promise that resolves to an Extension object.
   * @throws {Error} If the new local file doesn't exist.
   * @throws {Error} If the extension doesn't exist in the context.
   * @throws {AgentBayError} If update fails.
   */
  async update(extensionId: string, newLocalPath: string): Promise<Extension> {
    await this._ensureInitialized();
    
    if (!fs.existsSync(newLocalPath)) {
      throw new Error(`The specified new local file was not found: ${newLocalPath}`);
    }

    // Validate that the extension exists by checking the file list
    const existingExtensions = await this.list();
    const extensionExists = existingExtensions.some(ext => ext.id === extensionId);
    
    if (!extensionExists) {
      throw new Error(`Browser extension with ID '${extensionId}' not found in the context. Cannot update.`);
    }

    const remotePath = `${EXTENSIONS_BASE_PATH}/${extensionId}`;

    // Use the helper method to perform the cloud upload (overwrite)
    await this._uploadToCloud(newLocalPath, remotePath);

    return new Extension(extensionId, path.basename(newLocalPath));
  }

  /**
   * Gets detailed information about a specific browser extension.
   * 
   * @param extensionId - The ID of the extension to get info for.
   * @returns Promise that resolves to an Extension object if found, undefined otherwise.
   */
  private async _getExtensionInfo(extensionId: string): Promise<Extension | undefined> {
    await this._ensureInitialized();
    
    try {
      const extensions = await this.list();
      return extensions.find(ext => ext.id === extensionId);
    } catch (error) {
      logError(`An error occurred while getting extension info for '${extensionId}':`, error);
      return undefined;
    }
  }

  /**
   * Cleans up the auto-created context if it was created by this service.
   * 
   * @returns Promise that resolves to true if cleanup was successful or not needed, false if cleanup failed.
   * 
   * Note:
   *   This method only works if the context was auto-created by this service.
   *   For existing contexts, no cleanup is performed.
   */
  async cleanup(): Promise<boolean> {
    await this._ensureInitialized();
    
    if (!this.autoCreated) {
      // Context was not auto-created by this service, no cleanup needed
      return true;
    }

    try {
      const deleteResult = await this.contextService.delete(this.extensionContext);
      if (deleteResult) {
        log(`Extension context deleted: ${this.contextName} (ID: ${this.contextId})`);
        return true;
      } else {
        logError(`Warning: Failed to delete extension context: ${this.contextName}`, new Error('Delete operation returned false'));
        return false;
      }
    } catch (error) {
      logError(`Warning: Failed to delete extension context:`, error);
      return false;
    }
  }

  /**
   * Deletes a browser extension from the current context.
   * 
   * @param extensionId - ID of the extension to delete.
   * @returns Promise that resolves to true if deletion was successful, false otherwise.
   */
  async delete(extensionId: string): Promise<boolean> {
    await this._ensureInitialized();
    
    const remotePath = `${EXTENSIONS_BASE_PATH}/${extensionId}`;
    try {
      // Use context service to delete the file
      const deleteResult = await this.contextService.deleteFile(this.contextId, remotePath);

      return deleteResult.success;
    } catch (error) {
      logError(`An error occurred while deleting browser extension '${extensionId}':`, error);
      return false;
    }
  }

  /**
   * Create an ExtensionOption for the current context with specified extension IDs.
   * 
   * This is a convenience method that creates an ExtensionOption using the current
   * service's contextId and the provided extension IDs. This option can then be
   * used with BrowserContext for browser session creation.
   * 
   * @param extensionIds - List of extension IDs to include in the option.
   *                      These should be extensions that exist in the current context.
   * @returns ExtensionOption configuration object for browser extension integration.
   * @throws {Error} If extensionIds is empty or invalid.
   * 
   * @example
   * ```typescript
   * // Create extensions
   * const ext1 = await extensionsService.create("/path/to/ext1.zip");
   * const ext2 = await extensionsService.create("/path/to/ext2.zip");
   * 
   * // Create extension option for browser integration
   * const extOption = extensionsService.createExtensionOption([ext1.id, ext2.id]);
   * 
   * // Use with BrowserContext
   * const browserContext = new BrowserContext({
   *   contextId: "browser_session",
   *   autoUpload: true,
   *   extensionContextId: extOption.contextId,
   *   extensionIds: extOption.extensionIds
   * });
   * ```
   */
  createExtensionOption(extensionIds: string[]): ExtensionOption {
    // Note: This method is synchronous like in Python, but contextId might not be available yet
    // In practice, this should be called after the service has been used at least once
    if (!this.contextId) {
      throw new Error("Service not initialized. Please call an async method first or ensure context is created.");
    }
    
    return new ExtensionOption(
      this.contextId,
      extensionIds
    );
  }
}