/* eslint-disable @typescript-eslint/no-explicit-any, @typescript-eslint/no-unsafe-assignment, @typescript-eslint/no-unsafe-member-access */
import { AgentBay } from '../../src';
import { Context } from '../../src/context';
import { ContextService } from '../../src/context';

// Mock the ContextService
jest.mock('../../src/context', () => ({
    ContextService: jest.fn().mockImplementation(() => ({
        update: jest.fn(),
    })),
    Context: jest.fn().mockImplementation((id: string, name: string) => ({
        id,
        name,
    })),
}));

describe('AgentBay Browser Replay Context Update', () => {
    let agentBay: AgentBay;
    let mockContextService: jest.Mocked<ContextService>;

    beforeEach(() => {
        // Create a mock AgentBay instance
        agentBay = new AgentBay({ apiKey: 'test-api-key' });

        // Get the mocked context service
        mockContextService = agentBay.context as jest.Mocked<ContextService>;
    });

    afterEach(() => {
        jest.clearAllMocks();
    });

    describe('_updateBrowserReplayContext', () => {
        test('should successfully update browser replay context', async () => {
            // Mock response data
            const responseData = {
                appInstanceId: 'ai-0d67g8gz0l6tsd17i',
                sessionId: 'session-123',
                success: true
            };
            const recordContextId = 'record-context-123';

            // Mock successful context update
            mockContextService.update.mockResolvedValue({
                success: true,
                errorMessage: null
            } as any);

            // Call the private method using type assertion
            await (agentBay as any)._updateBrowserReplayContext(responseData, recordContextId);

            // Verify context.update was called with correct parameters
            expect(mockContextService.update).toHaveBeenCalledTimes(1);
            const contextObj = mockContextService.update.mock.calls[0][0];
            expect(contextObj.id).toBe(recordContextId);
            expect(contextObj.name).toBe('browserreplay-ai-0d67g8gz0l6tsd17i');
        });

        test('should not update context when recordContextId is empty', async () => {
            const responseData = {
                appInstanceId: 'ai-0d67g8gz0l6tsd17i',
                sessionId: 'session-123'
            };
            const recordContextId = '';

            await (agentBay as any)._updateBrowserReplayContext(responseData, recordContextId);

            // Verify context.update was not called
            expect(mockContextService.update).not.toHaveBeenCalled();
        });

        test('should not update context when AppInstanceId is missing', async () => {
            const responseData = {
                sessionId: 'session-123',
                success: true
            };
            const recordContextId = 'record-context-123';

            await (agentBay as any)._updateBrowserReplayContext(responseData, recordContextId);

            // Verify context.update was not called
            expect(mockContextService.update).not.toHaveBeenCalled();
        });

        test('should handle context update failure gracefully', async () => {
            const responseData = {
                appInstanceId: 'ai-0d67g8gz0l6tsd17i',
                sessionId: 'session-123',
                success: true
            };
            const recordContextId = 'record-context-123';

            // Mock failed context update
            mockContextService.update.mockResolvedValue({
                success: false,
                errorMessage: 'Context update failed'
            } as any);

            // Should not throw an exception
            await expect((agentBay as any)._updateBrowserReplayContext(responseData, recordContextId))
                .resolves.not.toThrow();

            // Verify context.update was called
            expect(mockContextService.update).toHaveBeenCalledTimes(1);
        });

        test('should handle context update exception gracefully', async () => {
            const responseData = {
                appInstanceId: 'ai-0d67g8gz0l6tsd17i',
                sessionId: 'session-123',
                success: true
            };
            const recordContextId = 'record-context-123';

            // Mock context update throwing an exception
            mockContextService.update.mockRejectedValue(new Error('Test error'));

            // Should not throw an exception
            await expect((agentBay as any)._updateBrowserReplayContext(responseData, recordContextId))
                .resolves.not.toThrow();

            // Verify context.update was called
            expect(mockContextService.update).toHaveBeenCalledTimes(1);
        });

        test('should handle null/undefined response data gracefully', async () => {
            const responseData = null;
            const recordContextId = 'record-context-123';

            await (agentBay as any)._updateBrowserReplayContext(responseData, recordContextId);

            // Verify context.update was not called
            expect(mockContextService.update).not.toHaveBeenCalled();
        });

        test('should create context name with correct prefix', async () => {
            const responseData = {
                appInstanceId: 'test-instance-123',
                sessionId: 'session-456'
            };
            const recordContextId = 'record-context-789';

            mockContextService.update.mockResolvedValue({
                success: true,
                errorMessage: null
            } as any);

            await (agentBay as any)._updateBrowserReplayContext(responseData, recordContextId);

            // Verify the context name has the correct prefix
            const contextObj = mockContextService.update.mock.calls[0][0];
            expect(contextObj.name).toBe('browserreplay-test-instance-123');
        });
    });
});
