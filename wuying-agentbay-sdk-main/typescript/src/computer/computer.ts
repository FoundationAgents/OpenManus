/**
 * Computer module for desktop UI automation.
 * Provides mouse, keyboard, and screen operations for desktop environments.
 */

import { OperationResult, WindowListResult, WindowInfoResult, BoolResult as WindowBoolResult } from "../types/api-response";

export enum MouseButton {
  LEFT = 'left',
  RIGHT = 'right',
  MIDDLE = 'middle',
  DOUBLE_LEFT = 'double_left'
}

export enum ScrollDirection {
  UP = 'up',
  DOWN = 'down',
  LEFT = 'left',
  RIGHT = 'right'
}

export interface BoolResult extends OperationResult {
  data?: boolean;
}

export interface CursorPosition extends OperationResult {
  x: number;
  y: number;
}

export interface ScreenSize extends OperationResult {
  width: number;
  height: number;
  dpiScalingFactor: number;
}

export interface ScreenshotResult extends OperationResult {
  data: string; // Screenshot URL
}

// Session interface for Computer module
interface ComputerSession {
  callMcpTool(toolName: string, args: Record<string, any>): Promise<any>;
  sessionId: string;
  getAPIKey(): string;
  getSessionId(): string;
}

export class Computer {
  private session: ComputerSession;

  constructor(session: ComputerSession) {
    this.session = session;
  }

  /**
   * Click mouse at specified coordinates.
   */
  async clickMouse(x: number, y: number, button: MouseButton | string = MouseButton.LEFT): Promise<BoolResult> {
    const buttonStr = typeof button === 'string' ? button : button;
    const validButtons = Object.values(MouseButton);
    if (!validButtons.includes(buttonStr as MouseButton)) {
      throw new Error(`Invalid button '${buttonStr}'. Must be one of ${validButtons.join(', ')}`);
    }

    const args = { x, y, button: buttonStr };
    try {
      const result = await this.session.callMcpTool('click_mouse', args);
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
        errorMessage: `Failed to click mouse: ${error instanceof Error ? error.message : String(error)}`,
        data: false
      };
    }
  }

  /**
   * Move mouse to specified coordinates.
   */
  async moveMouse(x: number, y: number): Promise<BoolResult> {
    const args = { x, y };
    try {
      const result = await this.session.callMcpTool('move_mouse', args);
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
        errorMessage: `Failed to move mouse: ${error instanceof Error ? error.message : String(error)}`,
        data: false
      };
    }
  }

  /**
   * Drag mouse from one position to another.
   */
  async dragMouse(fromX: number, fromY: number, toX: number, toY: number, button: MouseButton | string = MouseButton.LEFT): Promise<BoolResult> {
    const buttonStr = typeof button === 'string' ? button : button;
    const validButtons = [MouseButton.LEFT, MouseButton.RIGHT, MouseButton.MIDDLE];
    if (!validButtons.includes(buttonStr as MouseButton)) {
      throw new Error(`Invalid button '${buttonStr}'. Must be one of ${validButtons.join(', ')}`);
    }

    const args = { from_x: fromX, from_y: fromY, to_x: toX, to_y: toY, button: buttonStr };
    try {
      const result = await this.session.callMcpTool('drag_mouse', args);
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
        errorMessage: `Failed to drag mouse: ${error instanceof Error ? error.message : String(error)}`,
        data: false
      };
    }
  }

  /**
   * Scroll at specified coordinates.
   */
  async scroll(x: number, y: number, direction: ScrollDirection | string = ScrollDirection.UP, amount = 1): Promise<BoolResult> {
    const directionStr = typeof direction === 'string' ? direction : direction;
    const validDirections = Object.values(ScrollDirection);
    if (!validDirections.includes(directionStr as ScrollDirection)) {
      throw new Error(`Invalid direction '${directionStr}'. Must be one of ${validDirections.join(', ')}`);
    }

    const args = { x, y, direction: directionStr, amount };
    try {
      const result = await this.session.callMcpTool('scroll', args);
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
        errorMessage: `Failed to scroll: ${error instanceof Error ? error.message : String(error)}`,
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
   * Press keys.
   */
  async pressKeys(keys: string[], hold = false): Promise<BoolResult> {
    const args = { keys, hold };
    try {
      const result = await this.session.callMcpTool('press_keys', args);
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
        errorMessage: `Failed to press keys: ${error instanceof Error ? error.message : String(error)}`,
        data: false
      };
    }
  }

  /**
   * Release keys.
   */
  async releaseKeys(keys: string[]): Promise<BoolResult> {
    const args = { keys };
    try {
      const result = await this.session.callMcpTool('release_keys', args);
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
        errorMessage: `Failed to release keys: ${error instanceof Error ? error.message : String(error)}`,
        data: false
      };
    }
  }

  /**
   * Get cursor position.
   */
  async getCursorPosition(): Promise<CursorPosition> {
    try {
      const result = await this.session.callMcpTool('get_cursor_position', {});
      
      if (!result.success) {
        return {
          success: false,
          requestId: result.requestId || '',
          errorMessage: result.errorMessage || 'Failed to get cursor position',
          x: 0,
          y: 0
        };
      }

      // Parse JSON response from data field (callMcpTool already extracts content[0].text to data)
      const content = result.data;
      if (!content) {
        return {
          success: false,
          requestId: result.requestId || '',
          errorMessage: 'No content in response',
          x: 0,
          y: 0
        };
      }

      try {
        const position = JSON.parse(content);
        return {
          success: true,
          requestId: result.requestId || '',
          errorMessage: '',
          x: position.x || 0,
          y: position.y || 0
        };
      } catch (parseError) {
        return {
          success: false,
          requestId: result.requestId || '',
          errorMessage: `Failed to parse cursor position: ${parseError}`,
          x: 0,
          y: 0
        };
      }
    } catch (error) {
      return {
        success: false,
        requestId: '',
        errorMessage: `Failed to get cursor position: ${error instanceof Error ? error.message : String(error)}`,
        x: 0,
        y: 0
      };
    }
  }

  /**
   * Get screen size.
   */
  async getScreenSize(): Promise<ScreenSize> {
    try {
      const result = await this.session.callMcpTool('get_screen_size', {});
      
      if (!result.success) {
        return {
          success: false,
          requestId: result.requestId || '',
          errorMessage: result.errorMessage || 'Failed to get screen size',
          width: 0,
          height: 0,
          dpiScalingFactor: 1.0
        };
      }

      // Parse JSON response from data field (callMcpTool already extracts content[0].text to data)
      const content = result.data;
      if (!content) {
        return {
          success: false,
          requestId: result.requestId || '',
          errorMessage: 'No content in response',
          width: 0,
          height: 0,
          dpiScalingFactor: 1.0
        };
      }

      try {
        const screenInfo = JSON.parse(content);
        return {
          success: true,
          requestId: result.requestId || '',
          errorMessage: '',
          width: screenInfo.width || 0,
          height: screenInfo.height || 0,
          dpiScalingFactor: screenInfo.dpiScalingFactor || 1.0
        };
      } catch (parseError) {
        return {
          success: false,
          requestId: result.requestId || '',
          errorMessage: `Failed to parse screen size: ${parseError}`,
          width: 0,
          height: 0,
          dpiScalingFactor: 1.0
        };
      }
    } catch (error) {
      return {
        success: false,
        requestId: '',
        errorMessage: `Failed to get screen size: ${error instanceof Error ? error.message : String(error)}`,
        width: 0,
        height: 0,
        dpiScalingFactor: 1.0
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

      const screenshotUrl = result.content?.[0]?.text || '';
      return {
        success: true,
        requestId: result.requestId || '',
        errorMessage: '',
        data: screenshotUrl
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

  /**
   * Lists all root windows.
   */
  async listRootWindows(timeoutMs = 3000): Promise<WindowListResult> {
    const { WindowManager } = await import('../window/window');
    const windowManager = new WindowManager(this.session);
    return windowManager.listRootWindows(timeoutMs);
  }

  /**
   * Gets the currently active window.
   */
  async getActiveWindow(timeoutMs = 3000): Promise<WindowInfoResult> {
    const { WindowManager } = await import('../window/window');
    const windowManager = new WindowManager(this.session);
    return windowManager.getActiveWindow(timeoutMs);
  }

  /**
   * Activates the specified window.
   */
  async activateWindow(windowId: number): Promise<WindowBoolResult> {
    const { WindowManager } = await import('../window/window');
    const windowManager = new WindowManager(this.session);
    return windowManager.activateWindow(windowId);
  }

  /**
   * Closes the specified window.
   */
  async closeWindow(windowId: number): Promise<WindowBoolResult> {
    const { WindowManager } = await import('../window/window');
    const windowManager = new WindowManager(this.session);
    return windowManager.closeWindow(windowId);
  }

  /**
   * Maximizes the specified window.
   */
  async maximizeWindow(windowId: number): Promise<WindowBoolResult> {
    const { WindowManager } = await import('../window/window');
    const windowManager = new WindowManager(this.session);
    return windowManager.maximizeWindow(windowId);
  }

  /**
   * Minimizes the specified window.
   */
  async minimizeWindow(windowId: number): Promise<WindowBoolResult> {
    const { WindowManager } = await import('../window/window');
    const windowManager = new WindowManager(this.session);
    return windowManager.minimizeWindow(windowId);
  }

  /**
   * Restores the specified window.
   */
  async restoreWindow(windowId: number): Promise<WindowBoolResult> {
    const { WindowManager } = await import('../window/window');
    const windowManager = new WindowManager(this.session);
    return windowManager.restoreWindow(windowId);
  }

  /**
   * Resizes the specified window.
   */
  async resizeWindow(windowId: number, width: number, height: number): Promise<WindowBoolResult> {
    const { WindowManager } = await import('../window/window');
    const windowManager = new WindowManager(this.session);
    return windowManager.resizeWindow(windowId, width, height);
  }

  /**
   * Makes the specified window fullscreen.
   */
  async fullscreenWindow(windowId: number): Promise<WindowBoolResult> {
    const { WindowManager } = await import('../window/window');
    const windowManager = new WindowManager(this.session);
    return windowManager.fullscreenWindow(windowId);
  }

  /**
   * Toggles focus mode on or off.
   */
  async focusMode(on: boolean): Promise<WindowBoolResult> {
    const { WindowManager } = await import('../window/window');
    const windowManager = new WindowManager(this.session);
    return windowManager.focusMode(on);
  }
} 