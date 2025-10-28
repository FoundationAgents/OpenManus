
import { AgentBay, log, logError, CreateSessionParams, ContextSync, newSyncPolicy, ContextStatusData, newCreateSessionParams } from 'wuying-agentbay-sdk'



/**
 * Create a session with default parameters
 */
async function createSessionWithDefaultParams() {
  // Initialize the AgentBay client
  const agent_bay = new AgentBay({ apiKey: process.env.AGENTBAY_API_KEY });

  try {
    // Create a session with default parameters
    const result = await agent_bay.create();

    if (result.success && result.session) {
      log(`Session created successfully with ID: ${result.session.sessionId}`);
      log(`Request ID: ${result.requestId}`);

      // Clean up
      const deleteResult = await agent_bay.delete(result.session);
      if (deleteResult.success) {
        log('Session deleted successfully');
      } else {
        log(`Failed to delete session: ${deleteResult.errorMessage}`);
      }
    } else {
      log(`Failed to create session: ${result.errorMessage}`);
    }
  } catch (error) {
    logError('Error:', error);
  }
}

/**
 * Create a session with labels
 */
async function createSessionWithLabels() {
  // Initialize the AgentBay client
  const agent_bay = new AgentBay({ apiKey: process.env.AGENTBAY_API_KEY });

  try {
    // Define labels
    const labels = {
      environment: 'development',
      project: 'example',
      owner: 'user123'
    };

    // Create session parameters with labels
    const params: CreateSessionParams = {
      labels
    };

    // Create a session with the parameters
    const result = await agent_bay.create(params);

    if (result.success && result.session) {
      log(`Session with labels created successfully with ID: ${result.session.sessionId}`);
      log(`Request ID: ${result.requestId}`);

      // Verify the labels were set
      const labelResult = await result.session.getLabels();
      if (labelResult.success && labelResult.data) {
        log('Retrieved labels:');
        Object.entries(labelResult.data).forEach(([key, value]) => {
          log(`  ${key}: ${value}`);
        });
      }

      // Clean up
      const deleteResult = await agent_bay.delete(result.session);
      if (deleteResult.success) {
        log('Session deleted successfully');
      } else {
        log(`Failed to delete session: ${deleteResult.errorMessage}`);
      }
    } else {
      log(`Failed to create session with labels: ${result.errorMessage}`);
    }
  } catch (error) {
    logError('Error:', error);
  }
}

/**
 * Create a session with persistent context
 */
async function createSessionWithContext() {
  // Initialize the AgentBay client
  const agent_bay = new AgentBay({ apiKey: process.env.AGENTBAY_API_KEY });

  try {
    // Create or get a persistent context
    const contextResult = await agent_bay.context.get('example-context', true);

    if (contextResult.success && contextResult.context) {
      log(`Using context with ID: ${contextResult.context.id}`);

      // Create a session linked to the context
      const params = newCreateSessionParams()
        .addContextSync(contextResult.context.id, "/home/wuying");

      const sessionResult = await agent_bay.create(params);

      if (sessionResult.success && sessionResult.session) {
        log(`Session with context created successfully with ID: ${sessionResult.session.sessionId}`);
        log(`Request ID: ${sessionResult.requestId}`);

        // Clean up
        const deleteResult = await agent_bay.delete(sessionResult.session);
        if (deleteResult.success) {
          log('Session deleted successfully');
        } else {
          log(`Failed to delete session: ${deleteResult.errorMessage}`);
        }
      } else {
        log(`Failed to create session with context: ${sessionResult.errorMessage}`);
      }
    } else {
      log(`Failed to get or create context: ${contextResult.errorMessage}`);
    }
  } catch (error) {
    logError('Error:', error);
  }
}

/**
 * Create a session with context synchronization
 */
async function createSessionWithContextSync() {
  // Initialize the AgentBay client
  const agent_bay = new AgentBay({ apiKey: process.env.AGENTBAY_API_KEY });

  try {
    // Create or get a persistent context
    const contextResult = await agent_bay.context.get('example-sync-context', true);

    if (contextResult.success && contextResult.context) {
      log(`Using context with ID: ${contextResult.context.id}`);

      // Create a context sync configuration with default policy
      const contextId = contextResult.context.id;
      const path = '/mnt/persistent'
      const policy = newSyncPolicy();
      const contextSync = new ContextSync(contextId,path,policy);

      // Create a session with context synchronization
      const params: CreateSessionParams = {
        contextSync: [contextSync]
      };

      const sessionResult = await agent_bay.create(params);

      if (sessionResult.success && sessionResult.session) {
        log(`Session with context sync created successfully with ID: ${sessionResult.session.sessionId}`);
        log(`Request ID: ${sessionResult.requestId}`);

        // List the synchronized contexts
        // Wait for context to be synchronized
        await new Promise(resolve => setTimeout(resolve, 2000));

        const listResult = await sessionResult.session.context.info();
        if (listResult.requestId && listResult.contextStatusData.length > 0) {
          log(`Found ${listResult.contextStatusData.length} synchronized contexts:`);
          listResult.contextStatusData.forEach((ctx:ContextStatusData) => {

            log(`Context ID: ${ctx.contextId}, Path: ${ctx.path}, State: ${ctx.status}`);
          });
        }

        // Clean up
        const deleteResult = await agent_bay.delete(sessionResult.session);
        if (deleteResult.success) {
          log('Session deleted successfully');
        } else {
          log(`Failed to delete session: ${deleteResult.errorMessage}`);
        }
      } else {
        log(`Failed to create session with context sync: ${sessionResult.errorMessage}`);
      }
    } else {
      log(`Failed to get or create context: ${contextResult.errorMessage}`);
    }
  } catch (error) {
    logError('Error:', error);
  }
}

/**
 * Run all examples
 */
async function main() {
  log('1. Creating session with default parameters...');
  await createSessionWithDefaultParams();

  log('\n2. Creating session with labels...');
  await createSessionWithLabels();

  log('\n3. Creating session with context...');
  await createSessionWithContext();

  log('\n4. Creating session with context synchronization...');
  await createSessionWithContextSync();
}

main().catch(error => {
  logError('Error in main:', error);
  process.exit(1);
});
