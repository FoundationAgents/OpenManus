import { Session } from "../session";
import {
  UIElementListResult,
  BoolResult,
  OperationResult,
} from "../types/api-response";

/**
 * Key codes for UI operations
 */
export enum KeyCode {
  HOME = 3,
  BACK = 4,
  VOLUME_UP = 24,
  VOLUME_DOWN = 25,
  POWER = 26,
  MENU = 82
}

/**
 * Interface representing a UI element in the UI hierarchy
 */
export interface UIElement {
  bounds: string;
  className: string;
  text: string;
  type: string;
  resourceId: string;
  index: number;
  isParent: boolean;
  children?: UIElement[];
}



/**
 * Handles UI operations in the AgentBay cloud environment.
 * 
 * @deprecated This module is deprecated. Use Computer or Mobile modules instead.
 * - For desktop UI operations, use session.computer
 * - For mobile UI operations, use session.mobile
 */
export class UI {
  private session: Session;

  /**
   * Initialize a UI object.
   *
   * @param session - The Session instance that this UI belongs to.
   */
  constructor(session: {
    getAPIKey(): string;
    getClient(): any;
    getSessionId(): string;
    callMcpTool(toolName: string, args: any): Promise<{
      success: boolean;
      data: string;
      errorMessage: string;
      requestId: string;
    }>;
  }) {
    this.session = session as Session;
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
   * Retrieves all clickable UI elements within the specified timeout.
   * Corresponds to Python's get_clickable_ui_elements() method
   *
   * @param timeoutMs - The timeout in milliseconds. Default is 2000ms.
   * @returns UIElementListResult with clickable elements and requestId
   * @throws Error if the operation fails.
   * 
   * @deprecated Use session.computer.getClickableUIElements() for desktop or session.mobile.getClickableUIElements() for mobile instead.
   */
  async getClickableUIElements(timeoutMs = 2000): Promise<UIElementListResult> {
    console.warn('⚠️  UI.getClickableUIElements() is deprecated. Use session.computer.getClickableUIElements() for desktop or session.mobile.getClickableUIElements() for mobile instead.');
    
    try {
      const args = { timeout_ms: timeoutMs };
      const result = await this.session.callMcpTool("get_clickable_ui_elements", args);

      if (!result.success) {
        return {
          requestId: result.requestId,
          success: false,
          elements: [],
          errorMessage: result.errorMessage,
        };
      }

      let elements: UIElement[] = [];
      try {
        elements = JSON.parse(result.data);
      } catch (err) {
        return {
          requestId: result.requestId,
          success: false,
          elements: [],
          errorMessage: `Failed to parse UI elements: ${err}`,
        };
      }

      return {
        requestId: result.requestId,
        success: true,
        elements: elements,
      };
    } catch (error) {
      return {
        requestId: "",
        success: false,
        elements: [],
        errorMessage: `Failed to get clickable UI elements: ${error}`,
      };
    }
  }

  /**
   * Retrieves all UI elements regardless of their clickable status.
   * Corresponds to Python's get_all_ui_elements() method
   *
   * @param timeoutMs - The timeout in milliseconds. Default is 2000ms.
   * @returns UIElementListResult with all elements and requestId
   * @throws Error if the operation fails.
   * 
   * @deprecated Use session.computer.getAllUIElements() for desktop or session.mobile.getAllUIElements() for mobile instead.
   */
  async getAllUIElements(timeoutMs = 2000): Promise<UIElementListResult> {
    console.warn('⚠️  UI.getAllUIElements() is deprecated. Use session.computer.getAllUIElements() for desktop or session.mobile.getAllUIElements() for mobile instead.');
    
    try {
      const args = { timeout_ms: timeoutMs };
      const result = await this.session.callMcpTool("get_all_ui_elements", args);

      if (!result.success) {
        return {
          requestId: result.requestId,
          success: false,
          elements: [],
          errorMessage: result.errorMessage,
        };
      }

      let elements: UIElement[] = [];
      try {
        elements = JSON.parse(result.data);
      } catch (err) {
        return {
          requestId: result.requestId,
          success: false,
          elements: [],
          errorMessage: `Failed to parse UI elements: ${err}`,
        };
      }

      return {
        requestId: result.requestId,
        success: true,
        elements: elements,
      };
    } catch (error) {
      return {
        requestId: "",
        success: false,
        elements: [],
        errorMessage: `Failed to get all UI elements: ${error}`,
      };
    }
  }

  /**
   * Sends a key press event.
   * Corresponds to Python's send_key() method
   *
   * @param key - The key code to send. Supported key codes are:
   *   - 3 : HOME
   *   - 4 : BACK
   *   - 24 : VOLUME UP
   *   - 25 : VOLUME DOWN
   *   - 26 : POWER
   *   - 82 : MENU
   * @returns BoolResult with success status and requestId
   * @throws Error if the operation fails.
   * 
   * @deprecated Use session.computer.pressKeys() for desktop or session.mobile.sendKey() for mobile instead.
   */
  async sendKey(key: number): Promise<BoolResult> {
    console.warn('⚠️  UI.sendKey() is deprecated. Use session.computer.pressKeys() for desktop or session.mobile.sendKey() for mobile instead.');
    
    try {
      const args = { key };
      const result = await this.session.callMcpTool("send_key", args);

      return {
        requestId: result.requestId,
        success: result.success,
        data: result.success,
        errorMessage: result.errorMessage,
      };
    } catch (error) {
      return {
        requestId: "",
        success: false,
        data: false,
        errorMessage: `Failed to send key: ${error}`,
      };
    }
  }

  /**
   * Inputs text into the currently focused UI element.
   * Corresponds to Python's input_text() method
   *
   * @param text - The text to input
   * @returns BoolResult with success status and requestId
   * @throws Error if the operation fails.
   * 
   * @deprecated Use session.computer.inputText() for desktop or session.mobile.inputText() for mobile instead.
   */
  async inputText(text: string): Promise<BoolResult> {
    console.warn('⚠️  UI.inputText() is deprecated. Use session.computer.inputText() for desktop or session.mobile.inputText() for mobile instead.');
    
    try {
      const args = { text };
      const result = await this.session.callMcpTool("input_text", args);

      return {
        requestId: result.requestId,
        success: result.success,
        data: result.success,
        errorMessage: result.errorMessage,
      };
    } catch (error) {
      return {
        requestId: "",
        success: false,
        data: false,
        errorMessage: `Failed to input text: ${error}`,
      };
    }
  }

  /**
   * Performs a swipe gesture on the screen.
   * Corresponds to Python's swipe() method
   *
   * @param startX - The starting X coordinate
   * @param startY - The starting Y coordinate
   * @param endX - The ending X coordinate
   * @param endY - The ending Y coordinate
   * @param durationMs - The duration of the swipe in milliseconds. Default is 300ms.
   * @returns BoolResult with success status and requestId
   * @throws Error if the operation fails.
   * 
   * @deprecated Use session.computer.dragMouse() for desktop or session.mobile.swipe() for mobile instead.
   */
  async swipe(
    startX: number,
    startY: number,
    endX: number,
    endY: number,
    durationMs = 300
  ): Promise<BoolResult> {
    console.warn('⚠️  UI.swipe() is deprecated. Use session.computer.dragMouse() for desktop or session.mobile.swipe() for mobile instead.');
    
    try {
      const args = {
        start_x: startX,
        start_y: startY,
        end_x: endX,
        end_y: endY,
        duration_ms: durationMs,
      };
      const result = await this.session.callMcpTool("swipe", args);

      return {
        requestId: result.requestId,
        success: result.success,
        data: result.success,
        errorMessage: result.errorMessage,
      };
    } catch (error) {
      return {
        requestId: "",
        success: false,
        data: false,
        errorMessage: `Failed to perform swipe: ${error}`,
      };
    }
  }

  /**
   * Clicks on the screen at the specified coordinates.
   * Corresponds to Python's click() method
   *
   * @param x - The X coordinate
   * @param y - The Y coordinate
   * @param button - The mouse button to use. Default is 'left'
   * @returns BoolResult with success status and requestId
   * @throws Error if the operation fails.
   * 
   * @deprecated Use session.computer.clickMouse() for desktop or session.mobile.tap() for mobile instead.
   */
  async click(x: number, y: number, button = "left"): Promise<BoolResult> {
    console.warn('⚠️  UI.click() is deprecated. Use session.computer.clickMouse() for desktop or session.mobile.tap() for mobile instead.');
    
    try {
      const args = { x, y, button };
      const result = await this.session.callMcpTool("click", args);

      return {
        requestId: result.requestId,
        success: result.success,
        data: result.success,
        errorMessage: result.errorMessage,
      };
    } catch (error) {
      return {
        requestId: "",
        success: false,
        data: false,
        errorMessage: `Failed to click: ${error}`,
      };
    }
  }

  /**
   * Takes a screenshot of the current screen.
   * Corresponds to Python's screenshot() method
   *
   * @returns OperationResult with success status and requestId
   * @throws Error if the operation fails.
   * 
   * @deprecated Use session.computer.screenshot() for desktop or session.mobile.screenshot() for mobile instead.
   */
  async screenshot(): Promise<OperationResult> {
    console.warn('⚠️  UI.screenshot() is deprecated. Use session.computer.screenshot() for desktop or session.mobile.screenshot() for mobile instead.');
    
    try {
      const result = await this.session.callMcpTool("system_screenshot", {});

      if (!result.success) {
        return {
          requestId: result.requestId,
          success: false,
          data: "",
          errorMessage: result.errorMessage,
        };
      }

      return {
        requestId: result.requestId,
        success: true,
        data: result.data,
      };
    } catch (error) {
      return {
        requestId: "",
        success: false,
        data: "",
        errorMessage: `Failed to take screenshot: ${error}`,
      };
    }
  }
}
