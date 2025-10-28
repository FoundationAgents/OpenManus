/**
 * Functional validation helpers for Computer and Mobile modules.
 * These helpers verify that operations actually work by checking their effects.
 */

export interface FunctionalTestConfig {
  waitTimeAfterAction: number; // Wait time after each action (milliseconds)
  maxRetries: number; // Maximum retry attempts
  screenshotComparison: boolean; // Enable screenshot comparison
  uiElementTolerance: number; // UI element change tolerance (0.0-1.0)
  cursorPositionTolerance: number; // Cursor position tolerance in pixels
}

export interface FunctionalTestResult {
  testName: string;
  success: boolean;
  message: string;
  details: Record<string, any>;
  duration: number; // Duration in milliseconds
}

export function defaultFunctionalTestConfig(): FunctionalTestConfig {
  return {
    waitTimeAfterAction: 2000, // 2 seconds
    maxRetries: 3,
    screenshotComparison: true,
    uiElementTolerance: 0.3, // 30% change
    cursorPositionTolerance: 5, // 5 pixels
  };
}

export function createFunctionalTestResult(testName: string): FunctionalTestResult {
  return {
    testName,
    success: false,
    message: '',
    details: {},
    duration: 0,
  };
}

export function setTestSuccess(result: FunctionalTestResult, message: string): void {
  result.success = true;
  result.message = message;
}

export function setTestFailure(result: FunctionalTestResult, message: string): void {
  result.success = false;
  result.message = message;
}

export function addTestDetail(result: FunctionalTestResult, key: string, value: any): void {
  result.details[key] = value;
}

export function validateCursorPosition(
  cursorResult: any,
  screenResult: any,
  expectedX: number,
  expectedY: number,
  tolerance: number
): boolean {
  if (!cursorResult || !screenResult) {
    return false;
  }

  if (!cursorResult.success || !screenResult.success) {
    return false;
  }

  const cursorX = cursorResult.x;
  const cursorY = cursorResult.y;
  const screenWidth = screenResult.width;
  const screenHeight = screenResult.height;

  // Check if cursor is within screen bounds
  if (cursorX < 0 || cursorY < 0 || cursorX >= screenWidth || cursorY >= screenHeight) {
    return false;
  }

  // Check if cursor is within expected position tolerance
  const deltaX = Math.abs(cursorX - expectedX);
  const deltaY = Math.abs(cursorY - expectedY);

  return deltaX <= tolerance && deltaY <= tolerance;
}

export function validateScreenshotChanged(url1: string, url2: string): boolean {
  if (!url1 || !url2) {
    return false;
  }

  // Different URLs typically indicate different content
  // AgentBay generates new URLs for new screenshots
  return url1 !== url2;
}

export function validateScreenSize(screenResult: any): boolean {
  if (!screenResult || !screenResult.success) {
    return false;
  }

  const width = screenResult.width;
  const height = screenResult.height;
  const dpi = screenResult.dpiScalingFactor;

  // Screen dimensions should be positive and reasonable
  return (
    width > 0 &&
    height > 0 &&
    width <= 10000 &&
    height <= 10000 && // Max reasonable size
    dpi > 0 &&
    dpi <= 10 // Reasonable DPI range
  );
}

export interface SimplifiedUIElement {
  text: string;
  className: string;
  bounds: {
    left: number;
    top: number;
    right: number;
    bottom: number;
  };
}

export function convertMobileUIElements(elements: any[]): SimplifiedUIElement[] {
  const result: SimplifiedUIElement[] = [];
  for (const elem of elements) {
    if (elem) {
      const simplified: SimplifiedUIElement = {
        text: elem.text || '',
        className: elem.className || '',
        bounds: {
          left: elem.bounds?.left || 0,
          top: elem.bounds?.top || 0,
          right: elem.bounds?.right || 0,
          bottom: elem.bounds?.bottom || 0,
        },
      };
      result.push(simplified);
    }
  }
  return result;
}

export function validateUIElementsChanged(
  before: SimplifiedUIElement[],
  after: SimplifiedUIElement[],
  tolerance: number
): boolean {
  if (before.length === 0 && after.length === 0) {
    return false; // No elements in either case
  }

  // Calculate change ratio
  const totalElements = before.length + after.length;
  if (totalElements === 0) {
    return false;
  }

  // Simple comparison: check if element counts differ significantly
  const countDiff = Math.abs(after.length - before.length);
  if (countDiff / Math.max(before.length, 1) > tolerance) {
    return true;
  }

  // Check for text content changes
  const beforeTexts = new Set(before.map(elem => elem.text).filter(text => text));
  const afterTexts = new Set(after.map(elem => elem.text).filter(text => text));

  // Count text differences
  const beforeOnlyTexts = new Set([...beforeTexts].filter(text => !afterTexts.has(text)));
  const afterOnlyTexts = new Set([...afterTexts].filter(text => !beforeTexts.has(text)));
  const differentCount = beforeOnlyTexts.size + afterOnlyTexts.size;

  const changeRatio = differentCount / totalElements;
  return changeRatio > tolerance;
}

export function validateAppLaunched(
  beforeUI: SimplifiedUIElement[],
  afterUI: SimplifiedUIElement[]
): boolean {
  // App launch should result in significant UI changes (50% threshold)
  return validateUIElementsChanged(beforeUI, afterUI, 0.5);
}

export function findTextInputElement(elements: SimplifiedUIElement[]): SimplifiedUIElement | null {
  for (const elem of elements) {
    const className = elem.className.toLowerCase();
    if (
      className.includes('edittext') ||
      className.includes('textfield') ||
      className.includes('input')
    ) {
      return elem;
    }
  }
  return null;
}

export function calculateElementCenter(elem: SimplifiedUIElement): [number, number] {
  if (!elem) {
    return [0, 0];
  }

  const centerX = Math.floor((elem.bounds.left + elem.bounds.right) / 2);
  const centerY = Math.floor((elem.bounds.top + elem.bounds.bottom) / 2);
  return [centerX, centerY];
}

export function validateElementBounds(
  elem: SimplifiedUIElement,
  screenWidth: number,
  screenHeight: number
): boolean {
  if (!elem) {
    return false;
  }

  const { left, top, right, bottom } = elem.bounds;

  return (
    left >= 0 &&
    top >= 0 &&
    right <= screenWidth &&
    bottom <= screenHeight &&
    left < right &&
    top < bottom
  );
}

export async function safeScreenshot(
  computerOrMobile: any,
  testName: string
): Promise<[string | null, Error | null]> {
  try {
    if (!computerOrMobile) {
      return [null, null];
    }

    const result = await computerOrMobile.screenshot();
    if (!result) {
      return [null, null];
    }

    if (result.errorMessage) {
      return [null, new Error(result.errorMessage)];
    }

    if (result.data) {
      return [result.data, null];
    }

    return [null, null];
  } catch (error) {
    return [null, error instanceof Error ? error : new Error(String(error))];
  }
}

export async function waitWithTimeout(
  conditionFunc: () => boolean,
  timeout: number,
  checkInterval: number = 100
): Promise<boolean> {
  const startTime = Date.now();
  while (Date.now() - startTime < timeout) {
    if (conditionFunc()) {
      return true;
    }
    await new Promise(resolve => setTimeout(resolve, checkInterval));
  }
  return false;
}

export function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
} 