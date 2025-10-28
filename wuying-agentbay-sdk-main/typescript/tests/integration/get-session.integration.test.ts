/**
 * Integration test for GetSession API
 */

import { AgentBay } from '../../src/agent-bay';

describe('GetSession API Integration Test', () => {
  let agentBay: AgentBay;
  const apiKey = process.env.AGENTBAY_API_KEY;

  beforeAll(() => {
    if (!apiKey) {
      throw new Error('AGENTBAY_API_KEY environment variable is not set');
    }
    agentBay = new AgentBay({ apiKey });
  });

  it('should retrieve session information using GetSession API', async () => {
    // Create a session first
    console.log('Creating a new session for GetSession testing...');
    const createResult = await agentBay.create();
    expect(createResult.success).toBe(true);
    expect(createResult.session).toBeDefined();

    const session = createResult.session!;
    const sessionId = session.sessionId;
    console.log(`Session created with ID: ${sessionId}`);

    try {
      // Test GetSession API
      console.log('Testing GetSession API...');
      const getSessionResult = await agentBay.getSession(sessionId);

      // Validate response
      expect(getSessionResult.requestId).toBeTruthy();
      console.log(`GetSession RequestID: ${getSessionResult.requestId}`);

      expect(getSessionResult.httpStatusCode).toBe(200);
      expect(getSessionResult.code).toBe('ok');
      expect(getSessionResult.success).toBe(true);

      // Validate Data field
      expect(getSessionResult.data).toBeDefined();
      expect(getSessionResult.data!.sessionId).toBe(sessionId);
      expect(getSessionResult.data!.success).toBe(true);
      expect(getSessionResult.data!.appInstanceId).toBeTruthy();
      console.log(`AppInstanceID: ${getSessionResult.data!.appInstanceId}`);
      expect(getSessionResult.data!.resourceId).toBeTruthy();
      console.log(`ResourceID: ${getSessionResult.data!.resourceId}`);

      console.log('GetSession API test passed successfully');
    } finally {
      // Clean up: Delete the session
      console.log('Cleaning up: Deleting the session...');
      const deleteResult = await session.delete();
      if (deleteResult.success) {
        console.log(`Session ${sessionId} deleted successfully`);
      } else {
        console.warn(`Warning: Failed to delete session: ${deleteResult.errorMessage}`);
      }
    }
  });
});

