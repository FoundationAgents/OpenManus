/**
 * Mobile module for mobile UI automation.
 * Provides touch, input, and app management operations for mobile environments.
 */

import { OperationResult } from "../types/api-response";

export interface BoolResult extends OperationResult {
  data?: boolean;
}

export interface UIElement {
  text: string;
  className: string;
  bounds: {
    left: number;
    top: number;
    right: number;
    bottom: number;
  };
}

export interface UIElementsResult extends OperationResult {
  elements: UIElement[];
}

export interface InstalledApp {
  name: string;
  startCmd: string;
  workDirectory: string;
}

export interface InstalledAppsResult extends OperationResult {
  apps: InstalledApp[];
}

export interface Process {
  pid: number;
  pname: string;
}

export interface ProcessResult extends OperationResult {
  processes: Process[];
}

export interface ScreenshotResult extends OperationResult {
  data: string; // Screenshot URL
}

// Session interface for Mobile module
interface MobileSession {
  callMcpTool(toolName: string, args: Record<string, any>): Promise<any>;
  sessionId: string;
  getAPIKey(): string;
}

export class Mobile {
  private session: MobileSession;

  constructor(session: MobileSession) {
    this.session = session;
  }

  /**
   * Tap at specified coordinates.
   */
  async tap(x: number, y: number): Promise<BoolResult> {
    const args = { x, y };
    try {
      const result = await this.session.callMcpTool('tap', args);
      return {
        success: result.success || false,
        requestId: result.requestId || '',
        errorMessage: result.errorMessage || '',
        data: result.success || false
      };
    } catch (error) {
      return {
        success: false,
        requestId: '',
        errorMessage: `Failed to tap: ${error instanceof Error ? error.message : String(error)}`,
        data: false
      };
    }
  }

  /**
   * Swipe from one position to another.
   */
  async swipe(startX: number, startY: number, endX: number, endY: number, durationMs = 300): Promise<BoolResult> {
    const args = { start_x: startX, start_y: startY, end_x: endX, end_y: endY, duration_ms: durationMs };
    try {
      const result = await this.session.callMcpTool('swipe', args);
      return {
        success: result.success || false,
        requestId: result.requestId || '',
        errorMessage: result.errorMessage || '',
        data: result.success || false
      };
    } catch (error) {
      return {
        success: false,
        requestId: '',
        errorMessage: `Failed to swipe: ${error instanceof Error ? error.message : String(error)}`,
        data: false
      };
    }
  }

  /**
   * Input text.
   */
  async inputText(text: string): Promise<BoolResult> {
    const args = { text };
    try {
      const result = await this.session.callMcpTool('input_text', args);
      return {
        success: result.success || false,
        requestId: result.requestId || '',
        errorMessage: result.errorMessage || '',
        data: result.success || false
      };
    } catch (error) {
      return {
        success: false,
        requestId: '',
        errorMessage: `Failed to input text: ${error instanceof Error ? error.message : String(error)}`,
        data: false
      };
    }
  }

  /**
   * Send Android key code.
   */
  async sendKey(key: number): Promise<BoolResult> {
    const args = { key };
    try {
      const result = await this.session.callMcpTool('send_key', args);
      return {
        success: result.success || false,
        requestId: result.requestId || '',
        errorMessage: result.errorMessage || '',
        data: result.success || false
      };
    } catch (error) {
      return {
        success: false,
        requestId: '',
        errorMessage: `Failed to send key: ${error instanceof Error ? error.message : String(error)}`,
        data: false
      };
    }
  }

  /**
   * Get clickable UI elements.
   */
  async getClickableUIElements(timeoutMs = 5000): Promise<UIElementsResult> {
    const args = { timeout_ms: timeoutMs };
    try {
      const result = await this.session.callMcpTool('get_clickable_ui_elements', args);
      
      if (!result.success) {
        return {
          success: false,
          requestId: result.requestId || '',
          errorMessage: result.errorMessage || 'Failed to get clickable UI elements',
          elements: []
        };
      }

      if (!result.data) {
        return {
          success: true,
          requestId: result.requestId || '',
          errorMessage: '',
          elements: []
        };
      }

      try {
        const elements = JSON.parse(result.data);
        return {
          success: true,
          requestId: result.requestId || '',
          errorMessage: '',
          elements: elements || []
        };
      } catch (parseError) {
        return {
          success: false,
          requestId: result.requestId || '',
          errorMessage: `Failed to parse UI elements: ${parseError}`,
          elements: []
        };
      }
    } catch (error) {
      return {
        success: false,
        requestId: '',
        errorMessage: `Failed to get clickable UI elements: ${error instanceof Error ? error.message : String(error)}`,
        elements: []
      };
    }
  }

  /**
   * Get all UI elements.
   */
  async getAllUIElements(timeoutMs = 3000): Promise<UIElementsResult> {
    const args = { timeout_ms: timeoutMs };
    try {
      const result = await this.session.callMcpTool('get_all_ui_elements', args);
      
      if (!result.success) {
        return {
          success: false,
          requestId: result.requestId || '',
          errorMessage: result.errorMessage || 'Failed to get all UI elements',
          elements: []
        };
      }

      if (!result.data) {
        return {
          success: true,
          requestId: result.requestId || '',
          errorMessage: '',
          elements: []
        };
      }

      try {
        const elements = JSON.parse(result.data);
        return {
          success: true,
          requestId: result.requestId || '',
          errorMessage: '',
          elements: elements || []
        };
      } catch (parseError) {
        return {
          success: false,
          requestId: result.requestId || '',
          errorMessage: `Failed to parse UI elements: ${parseError}`,
          elements: []
        };
      }
    } catch (error) {
      return {
        success: false,
        requestId: '',
        errorMessage: `Failed to get all UI elements: ${error instanceof Error ? error.message : String(error)}`,
        elements: []
      };
    }
  }

  /**
   * Get installed apps.
   */
  async getInstalledApps(startMenu = false, desktop = true, ignoreSystemApps = true): Promise<InstalledAppsResult> {
    const args = { start_menu: startMenu, desktop, ignore_system_apps: ignoreSystemApps };
    try {
      const result = await this.session.callMcpTool('get_installed_apps', args);
      
      if (!result.success) {
        return {
          success: false,
          requestId: result.requestId || '',
          errorMessage: result.errorMessage || 'Failed to get installed apps',
          apps: []
        };
      }

      if (!result.data) {
        return {
          success: true,
          requestId: result.requestId || '',
          errorMessage: '',
          apps: []
        };
      }

      try {
        const apps = JSON.parse(result.data);
        return {
          success: true,
          requestId: result.requestId || '',
          errorMessage: '',
          apps: apps || []
        };
      } catch (parseError) {
        return {
          success: false,
          requestId: result.requestId || '',
          errorMessage: `Failed to parse installed apps: ${parseError}`,
          apps: []
        };
      }
    } catch (error) {
      return {
        success: false,
        requestId: '',
        errorMessage: `Failed to get installed apps: ${error instanceof Error ? error.message : String(error)}`,
        apps: []
      };
    }
  }

  /**
   * Start an app.
   */
  async startApp(startCmd: string, workDirectory = '', activity = ''): Promise<ProcessResult> {
    const args = { start_cmd: startCmd, work_directory: workDirectory, activity };
    try {
      const result = await this.session.callMcpTool('start_app', args);
      
      if (!result.success) {
        return {
          success: false,
          requestId: result.requestId || '',
          errorMessage: result.errorMessage || 'Failed to start app',
          processes: []
        };
      }

      if (!result.data) {
        return {
          success: true,
          requestId: result.requestId || '',
          errorMessage: '',
          processes: []
        };
      }

      try {
        const processes = JSON.parse(result.data);
        return {
          success: true,
          requestId: result.requestId || '',
          errorMessage: '',
          processes: processes || []
        };
      } catch (parseError) {
        return {
          success: false,
          requestId: result.requestId || '',
          errorMessage: `Failed to parse process result: ${parseError}`,
          processes: []
        };
      }
    } catch (error) {
      return {
        success: false,
        requestId: '',
        errorMessage: `Failed to start app: ${error instanceof Error ? error.message : String(error)}`,
        processes: []
      };
    }
  }

  /**
   * Stop app by package name.
   */
  async stopAppByPName(pname: string): Promise<BoolResult> {
    const args = { pname };
    try {
      const result = await this.session.callMcpTool('stop_app_by_pname', args);
      return {
        success: result.success || false,
        requestId: result.requestId || '',
        errorMessage: result.errorMessage || '',
        data: result.success || false
      };
    } catch (error) {
      return {
        success: false,
        requestId: '',
        errorMessage: `Failed to stop app: ${error instanceof Error ? error.message : String(error)}`,
        data: false
      };
    }
  }

  /**
   * Take a screenshot.
   */
  async screenshot(): Promise<ScreenshotResult> {
    try {
      const result = await this.session.callMcpTool('system_screenshot', {});
      
      if (!result.success) {
        return {
          success: false,
          requestId: result.requestId || '',
          errorMessage: result.errorMessage || 'Failed to take screenshot',
          data: ''
        };
      }

      return {
        success: true,
        requestId: result.requestId || '',
        errorMessage: '',
        data: result.data || ''
      };
    } catch (error) {
      return {
        success: false,
        requestId: '',
        errorMessage: `Failed to take screenshot: ${error instanceof Error ? error.message : String(error)}`,
        data: ''
      };
    }
  }
} 