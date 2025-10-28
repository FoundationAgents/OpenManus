import { Client } from "../api/client";
import {
  InstalledAppListResult,
  ProcessListResult,
  AppOperationResult,
} from "../types/api-response";


/**
 * Represents an installed application
 */
export interface InstalledApp {
  name: string;
  start_cmd: string;
  stop_cmd?: string;
  work_directory?: string;
}

/**
 * Represents a running process
 */
export interface Process {
  pname: string;
  pid: number;
  cmdline?: string;
  path?: string;
}

/**
 * Handles application operations in the AgentBay cloud environment.
 * 
 * @deprecated This module is deprecated. Use Computer or Mobile modules instead.
 * - For desktop applications, use session.computer
 * - For mobile applications, use session.mobile
 */
export class Application {
  private session: {
    getAPIKey(): string;
    getClient(): Client;
    getSessionId(): string;
    callMcpTool(toolName: string, args: any): Promise<{
      success: boolean;
      data: string;
      errorMessage: string;
      requestId: string;
    }>;
  };

  /**
   * Initialize an Application object.
   *
   * @param session - The Session instance that this Application belongs to.
   */
  constructor(session: {
    getAPIKey(): string;
    getClient(): Client;
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
   * Helper method to parse JSON string into objects
   */
  private parseJSON<T>(jsonString: string): T {
    try {
      return JSON.parse(jsonString);
    } catch (error) {
      throw new Error(`Failed to parse JSON: ${error}`);
    }
  }

  /**
   * Get a list of installed applications.
   *
   * @param startMenu - Whether to include start menu applications.
   * @param desktop - Whether to include desktop applications.
   * @param ignoreSystemApps - Whether to ignore system applications.
   * @returns A promise that resolves to the list of installed applications.
   * 
   * @deprecated Use session.computer.getInstalledApps() for desktop or session.mobile.getInstalledApps() for mobile instead.
   */
  async getInstalledApps(
    startMenu = false,
    desktop = true,
    ignoreSystemApps = true
  ): Promise<InstalledAppListResult> {
    console.warn('⚠️  Application.getInstalledApps() is deprecated. Use session.computer.getInstalledApps() for desktop or session.mobile.getInstalledApps() for mobile instead.');
    
    try {
      const args = {
        start_menu: startMenu,
        desktop,
        ignore_system_apps: ignoreSystemApps,
      };

      const result = await this.session.callMcpTool("get_installed_apps", args);

      if (!result.success) {
        return {
          requestId: result.requestId,
          success: false,
          data: [],
          errorMessage: result.errorMessage,
        };
      }

      let apps: InstalledApp[] = [];
      try {
        apps = this.parseJSON<InstalledApp[]>(result.data);
      } catch (err) {
        return {
          requestId: result.requestId,
          success: false,
          data: [],
          errorMessage: `Failed to parse installed apps: ${err}`,
        };
      }

      return {
        requestId: result.requestId,
        success: true,
        data: apps,
      };
    } catch (error) {
      return {
        requestId: "",
        success: false,
        data: [],
        errorMessage: `Failed to get installed apps: ${error}`,
      };
    }
  }

  /**
   * Start an application.
   *
   * @param startCmd - The command to start the application.
   * @param workDirectory - The working directory for the application.
   * @param activity - The activity to start (for mobile applications).
   * @returns A promise that resolves to the result of starting the application.
   * 
   * @deprecated Use session.computer.startApp() for desktop or session.mobile.startApp() for mobile instead.
   */
  async startApp(
    startCmd: string,
    workDirectory = "",
    activity = ""
  ): Promise<ProcessListResult> {
    console.warn('⚠️  Application.startApp() is deprecated. Use session.computer.startApp() for desktop or session.mobile.startApp() for mobile instead.');
    
    try {
      const args = {
        start_cmd: startCmd,
        work_directory: workDirectory,
        activity,
      };

      const result = await this.session.callMcpTool("start_app", args);

      if (!result.success) {
        return {
          requestId: result.requestId,
          success: false,
          data: [],
          errorMessage: result.errorMessage,
        };
      }

      let processes: Process[] = [];
      try {
        processes = this.parseJSON<Process[]>(result.data);
      } catch (err) {
        return {
          requestId: result.requestId,
          success: false,
          data: [],
          errorMessage: `Failed to parse processes: ${err}`,
        };
      }

      return {
        requestId: result.requestId,
        success: true,
        data: processes,
      };
    } catch (error) {
      return {
        requestId: "",
        success: false,
        data: [],
        errorMessage: `Failed to start app: ${error}`,
      };
    }
  }

  /**
   * Stop an application by process name.
   *
   * @param pname - The process name of the application to stop.
   * @returns A promise that resolves to the result of stopping the application.
   * 
   * @deprecated Use session.computer.stopAppByPName() for desktop or session.mobile.stopAppByPName() for mobile instead.
   */
  async stopAppByPName(pname: string): Promise<AppOperationResult> {
    console.warn('⚠️  Application.stopAppByPName() is deprecated. Use session.computer.stopAppByPName() for desktop or session.mobile.stopAppByPName() for mobile instead.');
    
    try {
      const args = { pname };
      const result = await this.session.callMcpTool("stop_app_by_pname", args);

      if (!result.success) {
        return {
          requestId: result.requestId,
          success: false,
          errorMessage: result.errorMessage,
        };
      }

      return {
        requestId: result.requestId,
        success: true,
      };
    } catch (error) {
      return {
        requestId: "",
        success: false,
        errorMessage: `Failed to stop app by process name: ${error}`,
      };
    }
  }

  /**
   * Stops an application by process ID.
   * Corresponds to Python's stop_app_by_pid() method
   *
   * @param pid - The process ID to stop.
   * @returns AppOperationResult with operation result and requestId
   * @throws Error if the operation fails.
   */
  async stopAppByPID(pid: number): Promise<AppOperationResult> {
    try {
      const args = { pid };
      const result = await this.session.callMcpTool("stop_app_by_pid", args);

      if (!result.success) {
        return {
          requestId: result.requestId,
          success: false,
          errorMessage: result.errorMessage,
        };
      }

      return {
        requestId: result.requestId,
        success: true,
      };
    } catch (error) {
      return {
        requestId: "",
        success: false,
        errorMessage: `Failed to stop app by process ID: ${error}`,
      };
    }
  }

  /**
   * Stop an application by command.
   *
   * @param cmd - The command to stop the application.
   * @returns A promise that resolves to the result of stopping the application.
   * 
   * @deprecated Use session.computer.stopAppByCmd() for desktop or session.mobile.stopAppByCmd() for mobile instead.
   */
  async stopAppByCmd(cmd: string): Promise<AppOperationResult> {
    console.warn('⚠️  Application.stopAppByCmd() is deprecated. Use session.computer.stopAppByCmd() for desktop or session.mobile.stopAppByCmd() for mobile instead.');
    
    try {
      const args = { stop_cmd: cmd };
      const result = await this.session.callMcpTool("stop_app_by_cmd", args);

      if (!result.success) {
        return {
          requestId: result.requestId,
          success: false,
          errorMessage: result.errorMessage,
        };
      }

      return {
        requestId: result.requestId,
        success: true,
      };
    } catch (error) {
      return {
        requestId: "",
        success: false,
        errorMessage: `Failed to stop app by command: ${error}`,
      };
    }
  }

  /**
   * Returns a list of currently visible applications.
   * Corresponds to Python's list_visible_apps() method
   *
   * @returns ProcessListResult with visible apps and requestId
   * @throws Error if the operation fails.
   */
  async listVisibleApps(): Promise<ProcessListResult> {
    try {
      const result = await this.session.callMcpTool("list_visible_apps", {});

      if (!result.success) {
        return {
          requestId: result.requestId,
          success: false,
          data: [],
          errorMessage: result.errorMessage,
        };
      }

      let processes: Process[] = [];
      try {
        processes = this.parseJSON<Process[]>(result.data);
      } catch (err) {
        return {
          requestId: result.requestId,
          success: false,
          data: [],
          errorMessage: `Failed to parse visible apps: ${err}`,
        };
      }

      return {
        requestId: result.requestId,
        success: true,
        data: processes,
      };
    } catch (error) {
      return {
        requestId: "",
        success: false,
        data: [],
        errorMessage: `Failed to list visible apps: ${error}`,
      };
    }
  }

  /**
   * Get a list of running processes.
   *
   * @returns A promise that resolves to the list of running processes.
   * 
   * @deprecated Use session.computer.getRunningProcesses() for desktop or session.mobile.getRunningProcesses() for mobile instead.
   */
  async getRunningProcesses(): Promise<ProcessListResult> {
    console.warn('⚠️  Application.getRunningProcesses() is deprecated. Use session.computer.getRunningProcesses() for desktop or session.mobile.getRunningProcesses() for mobile instead.');
    
    try {
      const result = await this.session.callMcpTool("list_running_processes", {});

      if (!result.success) {
        return {
          requestId: result.requestId,
          success: false,
          data: [],
          errorMessage: result.errorMessage,
        };
      }

      let processes: Process[] = [];
      try {
        processes = this.parseJSON<Process[]>(result.data);
      } catch (err) {
        return {
          requestId: result.requestId,
          success: false,
          data: [],
          errorMessage: `Failed to parse running processes: ${err}`,
        };
      }

      return {
        requestId: result.requestId,
        success: true,
        data: processes,
      };
    } catch (error) {
      return {
        requestId: "",
        success: false,
        data: [],
        errorMessage: `Failed to get running processes: ${error}`,
      };
    }
  }

  /**
   * Get a list of visible applications.
   *
   * @returns A promise that resolves to the list of visible applications.
   * 
   * @deprecated Use session.computer.getVisibleApps() for desktop instead. This API is not available for mobile.
   */
  async getVisibleApps(): Promise<InstalledAppListResult> {
    console.warn('⚠️  Application.getVisibleApps() is deprecated. Use session.computer.getVisibleApps() for desktop instead. This API is not available for mobile.');
    
    try {
      const result = await this.session.callMcpTool("list_visible_apps", {});

      if (!result.success) {
        return {
          requestId: result.requestId,
          success: false,
          data: [],
          errorMessage: result.errorMessage,
        };
      }

      let apps: InstalledApp[] = [];
      try {
        apps = this.parseJSON<InstalledApp[]>(result.data);
      } catch (err) {
        return {
          requestId: result.requestId,
          success: false,
          data: [],
          errorMessage: `Failed to parse visible apps: ${err}`,
        };
      }

      return {
        requestId: result.requestId,
        success: true,
        data: apps,
      };
    } catch (error) {
      return {
        requestId: "",
        success: false,
        data: [],
        errorMessage: `Failed to get visible apps: ${error}`,
      };
    }
  }
}
