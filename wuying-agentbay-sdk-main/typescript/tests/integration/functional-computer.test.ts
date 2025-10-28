/**
 * Computer module functional validation tests.
 * These tests validate that operations actually work by checking their effects.
 */

import { AgentBay } from '../../src/agent-bay';
import { CreateSessionParams } from '../../src/agent-bay';
import { Session } from '../../src/session';
import {
  defaultFunctionalTestConfig,
  createFunctionalTestResult,
  setTestSuccess,
  setTestFailure,
  addTestDetail,
  validateCursorPosition,
  validateScreenshotChanged,
  validateScreenSize,
  safeScreenshot,
  sleep,
  FunctionalTestConfig,
  FunctionalTestResult,
} from './functional-helpers';

describe('Computer Functional Validation', () => {
  let agentBay: AgentBay;
  let session: Session;
  let config: FunctionalTestConfig;

  beforeAll(async () => {
    // Skip if no API key provided
    const apiKey = process.env.AGENTBAY_API_KEY;
    if (!apiKey) {
      throw new Error('AGENTBAY_API_KEY environment variable not set');
    }

    // Create AgentBay client and session
    agentBay = new AgentBay({ apiKey });
    const sessionParams: CreateSessionParams = { imageId: 'linux_latest' };

    const sessionResult = await agentBay.create(sessionParams);
    expect(sessionResult.session).toBeDefined();

    session = sessionResult.session!;
    config = defaultFunctionalTestConfig();

    console.log(`Created Computer functional validation session: ${session.sessionId}`);

    // Wait for session to be ready
    await sleep(10000);
  }, 30000);

  afterAll(async () => {
    if (session) {
      try {
        const deleteResult = await session.delete();
        if (deleteResult && deleteResult.requestId) {
          console.log(`Session ${session.sessionId} deleted successfully`);
        }
      } catch (error) {
        console.error('Error deleting session:', error);
      }
    }
  }, 10000);

  test('Mouse Movement Validation', async () => {
    const result = createFunctionalTestResult('MouseMovementValidation');
    const startTime = Date.now();

    try {
      // Step 1: Get initial cursor position
      const initialCursor = await session.computer.getCursorPosition();
      if (initialCursor.errorMessage) {
        setTestFailure(result, `Failed to get initial cursor position: ${initialCursor.errorMessage}`);
        return;
      }

      addTestDetail(result, 'initial_cursor', {
        x: initialCursor.x,
        y: initialCursor.y,
      });

      // Step 2: Get screen size for safe movement
      const screen = await session.computer.getScreenSize();
      if (screen.errorMessage || !validateScreenSize(screen)) {
        setTestFailure(result, 'Invalid screen size');
        return;
      }

      addTestDetail(result, 'screen_size', {
        width: screen.width,
        height: screen.height,
        dpi: screen.dpiScalingFactor,
      });

      // Step 3: Move mouse to center of screen
      const targetX = Math.floor(screen.width / 2);
      const targetY = Math.floor(screen.height / 2);
      const moveResult = await session.computer.moveMouse(targetX, targetY);
      if (!moveResult.success) {
        setTestFailure(result, `Mouse move operation failed: ${moveResult.errorMessage}`);
        return;
      }

      // Wait for movement to complete
      await sleep(config.waitTimeAfterAction);

      // Step 4: Verify cursor position changed
      const newCursor = await session.computer.getCursorPosition();
      if (newCursor.errorMessage) {
        setTestFailure(result, `Failed to get new cursor position: ${newCursor.errorMessage}`);
        return;
      }

      addTestDetail(result, 'new_cursor', {
        x: newCursor.x,
        y: newCursor.y,
      });
      addTestDetail(result, 'target_position', { x: targetX, y: targetY });

      // Validate cursor movement
      if (validateCursorPosition(newCursor, screen, targetX, targetY, config.cursorPositionTolerance)) {
        setTestSuccess(result, 'Mouse movement validated successfully');
        console.log(
          `✅ Mouse moved from (${initialCursor.x},${initialCursor.y}) ` +
          `to (${newCursor.x},${newCursor.y}), target was (${targetX},${targetY})`
        );
      } else {
        setTestFailure(result, 'Cursor position validation failed');
        console.log(
          `❌ Mouse movement failed: expected (${targetX},${targetY}), ` +
          `got (${newCursor.x},${newCursor.y})`
        );
      }
    } finally {
      result.duration = Date.now() - startTime;
      console.log(`Test Result: ${JSON.stringify(result)}`);
    }

    expect(result.success).toBe(true);
  }, 60000);

  test('Screenshot Content Validation', async () => {
    const result = createFunctionalTestResult('ScreenshotContentValidation');
    const startTime = Date.now();

    try {
      // Step 1: Take initial screenshot
      const [screenshot1, error1] = await safeScreenshot(session.computer, 'initial');
      if (error1 || !screenshot1) {
        setTestFailure(result, 'Failed to take initial screenshot');
        return;
      }

      addTestDetail(result, 'screenshot1_url', screenshot1);

      // Step 2: Perform a visible action (move mouse to corner)
      const screen = await session.computer.getScreenSize();
      if (screen.errorMessage) {
        setTestFailure(result, 'Failed to get screen size');
        return;
      }

      // Move to top-left corner
      const moveResult = await session.computer.moveMouse(50, 50);
      if (!moveResult.success) {
        setTestFailure(result, `Failed to move mouse: ${moveResult.errorMessage}`);
        return;
      }

      // Wait for action to complete
      await sleep(config.waitTimeAfterAction);

      // Step 3: Take second screenshot
      const [screenshot2, error2] = await safeScreenshot(session.computer, 'after_move');
      if (error2 || !screenshot2) {
        setTestFailure(result, 'Failed to take second screenshot');
        return;
      }

      addTestDetail(result, 'screenshot2_url', screenshot2);

      // Validate screenshot change
      if (validateScreenshotChanged(screenshot1, screenshot2)) {
        setTestSuccess(result, 'Screenshot content validation successful');
        console.log(`✅ Screenshots changed: ${screenshot1} → ${screenshot2}`);
      } else {
        setTestFailure(result, 'Screenshots did not change as expected');
        console.log(`❌ Screenshots unchanged: ${screenshot1} = ${screenshot2}`);
      }
    } finally {
      result.duration = Date.now() - startTime;
      console.log(`Test Result: ${JSON.stringify(result)}`);
    }

    expect(result.success).toBe(true);
  }, 60000);

  test('Keyboard Input Validation', async () => {
    const result = createFunctionalTestResult('KeyboardInputValidation');
    const startTime = Date.now();

    try {
      // Step 1: Take initial screenshot
      const [screenshot1] = await safeScreenshot(session.computer, 'before_input');

      // Step 2: Click somewhere safe (center of screen) to focus
      const screen = await session.computer.getScreenSize();
      if (screen.errorMessage) {
        setTestFailure(result, 'Failed to get screen size');
        return;
      }

      const centerX = Math.floor(screen.width / 2);
      const centerY = Math.floor(screen.height / 2);
      const clickResult = await session.computer.clickMouse(centerX, centerY, 'left');
      if (!clickResult.success) {
        setTestFailure(result, `Failed to click for focus: ${clickResult.errorMessage}`);
        return;
      }

      await sleep(1000);

      // Step 3: Input test text
      const testText = 'AgentBay Functional Test';
      const inputResult = await session.computer.inputText(testText);
      if (!inputResult.success) {
        setTestFailure(result, `Failed to input text: ${inputResult.errorMessage}`);
        return;
      }

      addTestDetail(result, 'input_text', testText);
      await sleep(config.waitTimeAfterAction);

      // Step 4: Take screenshot after input
      const [screenshot2] = await safeScreenshot(session.computer, 'after_input');

      // Step 5: Select all text and delete it
      const selectResult = await session.computer.pressKeys(['Ctrl', 'a'], false);
      if (!selectResult.success) {
        setTestFailure(result, `Failed to select all: ${selectResult.errorMessage}`);
        return;
      }

      await sleep(500);

      const deleteResult = await session.computer.pressKeys(['Delete'], false);
      if (!deleteResult.success) {
        setTestFailure(result, `Failed to delete text: ${deleteResult.errorMessage}`);
        return;
      }

      await sleep(config.waitTimeAfterAction);

      // Step 6: Take final screenshot
      const [screenshot3] = await safeScreenshot(session.computer, 'after_delete');

      // Validate keyboard operations
      const inputChanged = validateScreenshotChanged(screenshot1 || '', screenshot2 || '');
      const deleteChanged = validateScreenshotChanged(screenshot2 || '', screenshot3 || '');

      addTestDetail(result, 'screenshots', {
        initial: screenshot1,
        after_input: screenshot2,
        after_delete: screenshot3,
      });
      addTestDetail(result, 'input_changed', inputChanged);
      addTestDetail(result, 'delete_changed', deleteChanged);

      if (inputChanged && deleteChanged) {
        setTestSuccess(result, 'Keyboard input validation successful');
        console.log('✅ Keyboard operations validated: input changed screen, delete changed screen');
      } else {
        setTestFailure(result, 'Keyboard operations did not produce expected visual changes');
        console.log(
          `❌ Keyboard validation failed: input_changed=${inputChanged}, delete_changed=${deleteChanged}`
        );
      }
    } finally {
      result.duration = Date.now() - startTime;
      console.log(`Test Result: ${JSON.stringify(result)}`);
    }

    expect(result.success).toBe(true);
  }, 60000);

  test('Screen Consistency Validation', async () => {
    const result = createFunctionalTestResult('ScreenConsistencyValidation');
    const startTime = Date.now();

    try {
      // Step 1: Get screen size
      const screen = await session.computer.getScreenSize();
      if (screen.errorMessage || !validateScreenSize(screen)) {
        setTestFailure(result, `Invalid screen size: ${screen.errorMessage}`);
        return;
      }

      addTestDetail(result, 'screen', {
        width: screen.width,
        height: screen.height,
        dpi: screen.dpiScalingFactor,
      });

      // Step 2: Test cursor positions at screen boundaries
      const testPositions: Array<[string, number, number]> = [
        ['top_left', 0, 0],
        ['top_right', screen.width - 1, 0],
        ['bottom_left', 0, screen.height - 1],
        ['bottom_right', screen.width - 1, screen.height - 1],
        ['center', Math.floor(screen.width / 2), Math.floor(screen.height / 2)],
      ];

      let allValid = true;
      const positionResults: Record<string, boolean> = {};

      for (const [name, x, y] of testPositions) {
        // Move to position
        const moveResult = await session.computer.moveMouse(x, y);
        if (!moveResult.success) {
          console.log(`Failed to move to ${name} (${x},${y}): ${moveResult.errorMessage}`);
          allValid = false;
          positionResults[name] = false;
          continue;
        }

        await sleep(500);

        // Get cursor position
        const cursor = await session.computer.getCursorPosition();
        if (cursor.errorMessage) {
          console.log(`Failed to get cursor at ${name}: ${cursor.errorMessage}`);
          allValid = false;
          positionResults[name] = false;
          continue;
        }

        // Validate position
        const valid = validateCursorPosition(cursor, screen, x, y, config.cursorPositionTolerance);
        positionResults[name] = valid;
        if (!valid) {
          allValid = false;
          console.log(`❌ Position ${name}: expected (${x},${y}), got (${cursor.x},${cursor.y})`);
        } else {
          console.log(`✅ Position ${name}: (${cursor.x},${cursor.y}) validated`);
        }
      }

      addTestDetail(result, 'position_results', positionResults);
      addTestDetail(result, 'all_positions_valid', allValid);

      if (allValid) {
        setTestSuccess(result, 'Screen consistency validation successful');
      } else {
        setTestFailure(result, 'Some cursor positions failed validation');
      }
    } finally {
      result.duration = Date.now() - startTime;
      console.log(`Test Result: ${JSON.stringify(result)}`);
    }

    expect(result.success).toBe(true);
  }, 60000);

  test('Complete Workflow Validation', async () => {
    const result = createFunctionalTestResult('CompleteWorkflowValidation');
    const startTime = Date.now();

    try {
      // This test combines multiple operations to validate a complete workflow
      const workflowSteps: string[] = [];
      const screenshots: Record<string, string | null> = {};

      // Step 1: Initial state
      const [screenshot] = await safeScreenshot(session.computer, 'workflow_start');
      screenshots.start = screenshot;
      workflowSteps.push('Initial screenshot taken');

      // Step 2: Get screen info and move to center
      const screen = await session.computer.getScreenSize();
      if (screen.errorMessage) {
        setTestFailure(result, 'Failed to get screen size');
        return;
      }

      const centerX = Math.floor(screen.width / 2);
      const centerY = Math.floor(screen.height / 2);
      const moveResult = await session.computer.moveMouse(centerX, centerY);
      if (moveResult.success) {
        workflowSteps.push('Moved mouse to center');
      }

      await sleep(1000);

      // Step 3: Click and input text
      const clickResult = await session.computer.clickMouse(centerX, centerY, 'left');
      if (clickResult.success) {
        workflowSteps.push('Clicked at center');
      }

      const inputResult = await session.computer.inputText('Workflow Test');
      if (inputResult.success) {
        workflowSteps.push('Input text');
      }

      await sleep(config.waitTimeAfterAction);

      // Step 4: Screenshot after input
      const [screenshot2] = await safeScreenshot(session.computer, 'workflow_input');
      screenshots.after_input = screenshot2;

      // Step 5: Select and copy text
      const selectResult = await session.computer.pressKeys(['Ctrl', 'a'], false);
      if (selectResult.success) {
        workflowSteps.push('Selected all text');
      }

      const copyResult = await session.computer.pressKeys(['Ctrl', 'c'], false);
      if (copyResult.success) {
        workflowSteps.push('Copied text');
      }

      // Step 6: Delete and paste
      const deleteResult = await session.computer.pressKeys(['Delete'], false);
      if (deleteResult.success) {
        workflowSteps.push('Deleted text');
      }

      await sleep(1000);

      const pasteResult = await session.computer.pressKeys(['Ctrl', 'v'], false);
      if (pasteResult.success) {
        workflowSteps.push('Pasted text');
      }

      await sleep(config.waitTimeAfterAction);

      // Step 7: Final screenshot
      const [screenshot3] = await safeScreenshot(session.computer, 'workflow_end');
      screenshots.end = screenshot3;

      // Validate workflow
      const inputChanged = validateScreenshotChanged(screenshots.start || '', screenshots.after_input || '');
      const workflowCompleted = validateScreenshotChanged(screenshots.after_input || '', screenshots.end || '');

      addTestDetail(result, 'workflow_steps', workflowSteps);
      addTestDetail(result, 'screenshots', screenshots);
      addTestDetail(result, 'input_changed', inputChanged);
      addTestDetail(result, 'workflow_completed', workflowCompleted);

      if (workflowSteps.length >= 6 && inputChanged) {
        setTestSuccess(result, 'Complete workflow validation successful');
        console.log(`✅ Workflow completed: ${workflowSteps.length} steps, visual changes confirmed`);
      } else {
        setTestFailure(result, 'Workflow validation failed');
        console.log(`❌ Workflow failed: ${workflowSteps.length} steps, input_changed=${inputChanged}`);
      }
    } finally {
      result.duration = Date.now() - startTime;
      console.log(`Test Result: ${JSON.stringify(result)}`);
    }

    expect(result.success).toBe(true);
  }, 90000);
}); 