/**
 * Unit tests for Computer module.
 * Following TDD principles - tests first, then implementation.
 */

import { Computer, MouseButton, ScrollDirection } from '../../src/computer/computer';
import { Session } from '../../src/session';

// Mock Session interface
interface MockSession {
  callMcpTool: jest.Mock;
  getAPIKey: () => string;
  sessionId: string;
}

describe('Computer', () => {
  let mockSession: MockSession;
  let computer: Computer;

  beforeEach(() => {
    mockSession = {
      callMcpTool: jest.fn(),
      getAPIKey: () => 'test-api-key',
      sessionId: 'test-session-id'
    };
    computer = new Computer(mockSession as any);
  });

  describe('Mouse Operations', () => {
    test('clickMouse should call MCP tool with correct parameters', async () => {
      // Arrange
      const mockResult = {
        success: true,
        requestId: 'test-123',
        errorMessage: ''
      };
      mockSession.callMcpTool.mockResolvedValue(mockResult);

      // Act
      const result = await computer.clickMouse(100, 200, 'left');

      // Assert
      expect(mockSession.callMcpTool).toHaveBeenCalledWith('click_mouse', {
        x: 100,
        y: 200,
        button: 'left'
      });
      expect(result.success).toBe(true);
      expect(result.requestId).toBe('test-123');
    });

    test('clickMouse should validate button parameter', async () => {
      // Act & Assert
      await expect(computer.clickMouse(100, 200, 'invalid' as any))
        .rejects.toThrow('Invalid button');
    });

    test('moveMouse should call MCP tool with correct parameters', async () => {
      // Arrange
      const mockResult = {
        success: true,
        requestId: 'test-123'
      };
      mockSession.callMcpTool.mockResolvedValue(mockResult);

      // Act
      const result = await computer.moveMouse(150, 250);

      // Assert
      expect(mockSession.callMcpTool).toHaveBeenCalledWith('move_mouse', {
        x: 150,
        y: 250
      });
      expect(result.success).toBe(true);
    });

    test('dragMouse should call MCP tool with correct parameters', async () => {
      // Arrange
      const mockResult = {
        success: true,
        requestId: 'test-123'
      };
      mockSession.callMcpTool.mockResolvedValue(mockResult);

      // Act
      const result = await computer.dragMouse(100, 100, 200, 200, 'left');

      // Assert
      expect(mockSession.callMcpTool).toHaveBeenCalledWith('drag_mouse', {
        from_x: 100,
        from_y: 100,
        to_x: 200,
        to_y: 200,
        button: 'left'
      });
      expect(result.success).toBe(true);
    });

    test('scroll should call MCP tool with correct parameters', async () => {
      // Arrange
      const mockResult = {
        success: true,
        requestId: 'test-123'
      };
      mockSession.callMcpTool.mockResolvedValue(mockResult);

      // Act
      const result = await computer.scroll(100, 200, 'up', 3);

      // Assert
      expect(mockSession.callMcpTool).toHaveBeenCalledWith('scroll', {
        x: 100,
        y: 200,
        direction: 'up',
        amount: 3
      });
      expect(result.success).toBe(true);
    });

    test('scroll should validate direction parameter', async () => {
      // Act & Assert
      await expect(computer.scroll(100, 200, 'invalid' as any, 1))
        .rejects.toThrow('Invalid direction');
    });

    test('clickMouse should accept MouseButton enum', async () => {
      // Arrange
      const mockResult = {
        success: true,
        requestId: 'test-123'
      };
      mockSession.callMcpTool.mockResolvedValue(mockResult);

      // Act
      const result = await computer.clickMouse(100, 200, MouseButton.RIGHT);

      // Assert
      expect(mockSession.callMcpTool).toHaveBeenCalledWith('click_mouse', {
        x: 100,
        y: 200,
        button: 'right'
      });
      expect(result.success).toBe(true);
    });

    test('clickMouse should accept MouseButton.DOUBLE_LEFT enum', async () => {
      // Arrange
      const mockResult = {
        success: true,
        requestId: 'test-123'
      };
      mockSession.callMcpTool.mockResolvedValue(mockResult);

      // Act
      const result = await computer.clickMouse(100, 200, MouseButton.DOUBLE_LEFT);

      // Assert
      expect(mockSession.callMcpTool).toHaveBeenCalledWith('click_mouse', {
        x: 100,
        y: 200,
        button: 'double_left'
      });
      expect(result.success).toBe(true);
    });

    test('dragMouse should accept MouseButton enum', async () => {
      // Arrange
      const mockResult = {
        success: true,
        requestId: 'test-123'
      };
      mockSession.callMcpTool.mockResolvedValue(mockResult);

      // Act
      const result = await computer.dragMouse(100, 100, 200, 200, MouseButton.MIDDLE);

      // Assert
      expect(mockSession.callMcpTool).toHaveBeenCalledWith('drag_mouse', {
        from_x: 100,
        from_y: 100,
        to_x: 200,
        to_y: 200,
        button: 'middle'
      });
      expect(result.success).toBe(true);
    });

    test('scroll should accept ScrollDirection enum', async () => {
      // Arrange
      const mockResult = {
        success: true,
        requestId: 'test-123'
      };
      mockSession.callMcpTool.mockResolvedValue(mockResult);

      // Act
      const result = await computer.scroll(100, 200, ScrollDirection.DOWN, 5);

      // Assert
      expect(mockSession.callMcpTool).toHaveBeenCalledWith('scroll', {
        x: 100,
        y: 200,
        direction: 'down',
        amount: 5
      });
      expect(result.success).toBe(true);
    });
  });

  describe('Keyboard Operations', () => {
    test('inputText should call MCP tool with correct parameters', async () => {
      // Arrange
      const mockResult = {
        success: true,
        requestId: 'test-123'
      };
      mockSession.callMcpTool.mockResolvedValue(mockResult);

      // Act
      const result = await computer.inputText('Hello World');

      // Assert
      expect(mockSession.callMcpTool).toHaveBeenCalledWith('input_text', {
        text: 'Hello World'
      });
      expect(result.success).toBe(true);
    });

    test('pressKeys should call MCP tool with correct parameters', async () => {
      // Arrange
      const mockResult = {
        success: true,
        requestId: 'test-123'
      };
      mockSession.callMcpTool.mockResolvedValue(mockResult);

      // Act
      const result = await computer.pressKeys(['Ctrl', 'C'], false);

      // Assert
      expect(mockSession.callMcpTool).toHaveBeenCalledWith('press_keys', {
        keys: ['Ctrl', 'C'],
        hold: false
      });
      expect(result.success).toBe(true);
    });

    test('releaseKeys should call MCP tool with correct parameters', async () => {
      // Arrange
      const mockResult = {
        success: true,
        requestId: 'test-123'
      };
      mockSession.callMcpTool.mockResolvedValue(mockResult);

      // Act
      const result = await computer.releaseKeys(['Ctrl', 'C']);

      // Assert
      expect(mockSession.callMcpTool).toHaveBeenCalledWith('release_keys', {
        keys: ['Ctrl', 'C']
      });
      expect(result.success).toBe(true);
    });
  });

  describe('Screen Operations', () => {
    test('getCursorPosition should call MCP tool and return position', async () => {
      // Arrange
      const mockResult = {
        success: true,
        requestId: 'test-123',
        data: '{"x":100,"y":200}'
      };
      mockSession.callMcpTool.mockResolvedValue(mockResult);

      // Act
      const result = await computer.getCursorPosition();

      // Assert
      expect(mockSession.callMcpTool).toHaveBeenCalledWith('get_cursor_position', {});
      expect(result.x).toBe(100);
      expect(result.y).toBe(200);
    });

    test('getScreenSize should call MCP tool and return screen info', async () => {
      // Arrange
      const mockResult = {
        success: true,
        requestId: 'test-123',
        data: '{"width":1920,"height":1080,"dpiScalingFactor":1.0}'
      };
      mockSession.callMcpTool.mockResolvedValue(mockResult);

      // Act
      const result = await computer.getScreenSize();

      // Assert
      expect(mockSession.callMcpTool).toHaveBeenCalledWith('get_screen_size', {});
      expect(result.width).toBe(1920);
      expect(result.height).toBe(1080);
      expect(result.dpiScalingFactor).toBe(1.0);
    });

    test('screenshot should call MCP tool and return URL', async () => {
      // Arrange
      const mockResult = {
        success: true,
        requestId: 'test-123',
        content: [{ text: 'https://example.com/screenshot.png' }]
      };
      mockSession.callMcpTool.mockResolvedValue(mockResult);

      // Act
      const result = await computer.screenshot();

      // Assert
      expect(mockSession.callMcpTool).toHaveBeenCalledWith('system_screenshot', {});
      expect(result.data).toBe('https://example.com/screenshot.png');
    });
  });

  describe('Error Handling', () => {
    test('should handle MCP tool errors gracefully', async () => {
      // Arrange
      const mockError = new Error('MCP tool failed');
      mockSession.callMcpTool.mockRejectedValue(mockError);

      // Act
      const result = await computer.clickMouse(100, 200);

      // Assert
      expect(result.success).toBe(false);
      expect(result.errorMessage).toContain('MCP tool failed');
    });

    test('should handle invalid JSON response', async () => {
      // Arrange
      const mockResult = {
        success: true,
        requestId: 'test-123',
        data: 'invalid json'
      };
      mockSession.callMcpTool.mockResolvedValue(mockResult);

      // Act
      const result = await computer.getCursorPosition();

      // Assert
      expect(result.success).toBe(false);
      expect(result.errorMessage).toContain('Failed to parse');
    });
  });
}); 