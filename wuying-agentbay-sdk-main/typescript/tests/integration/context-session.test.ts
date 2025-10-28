import { AgentBay, Session, Context, ContextSync } from "../../src";
import { getTestApiKey, wait } from "../utils/test-helpers";
import { log } from "../../src/utils/logger";

// Define test runner types if they're not available
declare function describe(name: string, fn: () => void): void;
declare function beforeEach(fn: () => void | Promise<void>): void;
declare function afterEach(fn: () => void | Promise<void>): void;
declare function it(name: string, fn: () => void | Promise<void>): void;
declare function expect(actual: any): any;

describe("Context Session Integration", () => {
  let agentBay: AgentBay;

  beforeEach(async () => {
    const apiKey = getTestApiKey();
    agentBay = new AgentBay({ apiKey });
    log(`AgentBay client initialized successfully`);
  });

  describe("Context Session Management", () => {
    it("should manage context and session lifecycle correctly", async () => {
      // Step 1: Create a new context
      const contextName = `test-context-${Date.now()}`;
      log(`Creating new context with name: ${contextName}`);

      const createContextResponse = await agentBay.context.create(contextName);
      const context = createContextResponse.context;
      if (!context) {
        throw new Error("Failed to create context");
      }
      log(
        `Context created successfully - ID: ${context.id}, Name: ${context.name}, State: ${context.state}`
      );
      log(
        `Create Context RequestId: ${
          createContextResponse.requestId || "undefined"
        }`
      );

      expect(context.id).toBeDefined();
      expect(context.name).toBe(contextName);

      try {
        // Step 2: Create a session with the context ID (expect success)
        log("Step 2: Creating first session with context ID...");
        const createSessionResponse = await agentBay.create({
          contextSync: [
            new ContextSync(context.id, "/home/wuying")
          ],
        });
        const session1 = createSessionResponse.session!;
        log(`Session created successfully with ID: ${session1.sessionId}`);
        log(
          `Create Session RequestId: ${
            createSessionResponse.requestId || "undefined"
          }`
        );

        
        // Step 4: Try to create another session with the same context_id (may succeed now)
        log(
          "Step 4: Attempting to create a second session with the same context ID..."
        );
        
        // Note: With the new context sync approach, it may now be possible to create multiple
        // sessions with the same context ID, as the context state management has changed.
        // This is expected behavior with the new implementation.
        const createSession2Response = await agentBay.create({
          contextSync: [
            new ContextSync(context.id, "/home/wuying")
          ],
        });
        const session2 = createSession2Response.session!;

        log(
          `Successfully created second session with ID: ${session2.sessionId}`
        );
        log(
          `Create Session 2 RequestId: ${
            createSession2Response.requestId || "undefined"
          }`
        );
        
        // Clean up the second session
        const deleteSession2Response = await session2.delete();
        log(
          `Delete Session 2 RequestId: ${
            deleteSession2Response.requestId || "undefined"
          }`
        );

        // Step 3: Release the first session
        log("Step 3: Releasing the first session...");
        const deleteSession1Response = await session1.delete();
        log("First session released successfully");
        log(
          `Delete Session 1 RequestId: ${
            deleteSession1Response.requestId || "undefined"
          }`
        );

        // Wait for the system to update the context status
        log("Waiting for context status to update...");
        await wait(15000); // Increased from 3s to 15s to allow more time for resources to be released

        // Step 4: Create another session with the same context_id (expect success)
        log("Step 4: Creating a new session with the same context ID...");
        const createSession3Response = await agentBay.create({
          contextSync: [
            new ContextSync(context.id, "/home/wuying")
          ],
        });
        const session3 = createSession3Response.session!;
        log(`New session created successfully with ID: ${session3.sessionId}`);
        log(
          `Create Session 3 RequestId: ${
            createSession3Response.requestId || "undefined"
          }`
        );

        // Step 5: Clean up by releasing the session
        log("Step 5: Cleaning up - releasing the third session...");
        const deleteSession3Response = await session3.delete();
        log("Third session released successfully");
        log(
          `Delete Session 3 RequestId: ${
            deleteSession3Response.requestId || "undefined"
          }`
        );
      } finally {
        // Clean up the context
        log("Cleaning up: Deleting the context...");
        try {
          const deleteContextResponse = await agentBay.context.delete(context);
          log(`Context ${context.id} deleted successfully`);
          log(
            `Delete Context RequestId: ${
              deleteContextResponse.requestId || "undefined"
            }`
          );
        } catch (error) {
          log(`Warning: Error deleting context: ${error}`);
        }
      }
    });
  });

  describe("Context Lifecycle", () => {
    it("should manage the complete lifecycle of a context", async () => {
      // Get initial list of contexts for comparison
      log("Getting initial list of contexts...");
      const initialContextsResponse = await agentBay.context.list();
      const initialContexts = initialContextsResponse.contexts;
      log(`Found ${initialContexts.length} contexts initially`);
      log(
        `List Initial Contexts RequestId: ${
          initialContextsResponse.requestId || "undefined"
        }`
      );

      // Store initial context IDs for comparison
      const initialContextIDs = new Map<string, boolean>();
      for (const ctx of initialContexts) {
        initialContextIDs.set(ctx.id, true);
        log(`Initial context: ${ctx.name} (${ctx.id})`);
      }

      // Step 1: Create a new context
      log("Step 1: Creating a new context...");
      const contextName = `test-context-${Date.now()}`;
      const createContextResponse = await agentBay.context.create(contextName);
      const context = createContextResponse.context;
      if (!context) {
        throw new Error("Failed to create context");
      }
      log(`Created context: ${context.name} (${context.id})`);
      log(
        `Create Context RequestId: ${
          createContextResponse.requestId || "undefined"
        }`
      );

      // Verify the created context has the expected name
      expect(context.name).toBe(contextName);
      expect(context.id).toBeDefined();

      // Store the original context ID for later verification
      const originalContextID = context.id;

      try {
        // Step 2: Get the context we just created
        log("Step 2: Getting the context we just created...");
        const getContextResponse = await agentBay.context.get(contextName);
        const retrievedContext = getContextResponse.context;
        if (!retrievedContext) {
          throw new Error("Failed to retrieve context");
        }
        log(
          `Successfully retrieved context: ${retrievedContext.name} (${retrievedContext.id})`
        );
        log(
          `Get Context RequestId: ${
            getContextResponse.requestId || "undefined"
          }`
        );

        // Verify the retrieved context matches what we created
        expect(retrievedContext.name).toBe(contextName);
        expect(retrievedContext.id).toBe(originalContextID);

        // Step 3: List contexts and verify our new context is in the list
        log("Step 3: Listing all contexts...");
        const listContextsResponse = await agentBay.context.list();
        const allContexts = listContextsResponse.contexts;
        log(
          `List All Contexts RequestId: ${
            listContextsResponse.requestId || "undefined"
          }`
        );

        // Verify the list contains our new context
        let foundInList = false;
        for (const c of allContexts) {
          if (c.id === originalContextID) {
            foundInList = true;
            expect(c.name).toBe(contextName);
            break;
          }
        }
        expect(foundInList).toBe(true);
        log("Successfully listed contexts, found our context in the list");

        // Step 4: Create a session with the context
        log("Step 4: Creating a session with the context...");
        const createSessionResponse = await agentBay.create({
          contextSync: [
            new ContextSync(context.id, "/home/wuying")
          ],
          labels: {
            username: "test-user",
            project: "test-project",
          },
        });
        const session = createSessionResponse.session!;
        log(`Session created with ID: ${session.sessionId}`);
        log(
          `Create Session RequestId: ${
            createSessionResponse.requestId || "undefined"
          }`
        );

        try {
          // Step 5: Update the context
          log("Step 5: Updating the context...");
          const updatedName = `updated-${contextName}`;
          context.name = updatedName;
          const updateContextResponse = await agentBay.context.update(context);
          log("Context update reported as successful");
          log(
            `Update Context RequestId: ${
              updateContextResponse.requestId || "undefined"
            }`
          );

          // Step 6: Verify the update by getting the context again
          log("Step 6: Verifying the update by getting the context again...");
          const getUpdatedContextResponse = await agentBay.context.get(
            updatedName
          );
          const retrievedUpdatedContext = getUpdatedContextResponse.context;
          if (!retrievedUpdatedContext) {
            throw new Error("Failed to retrieve updated context");
          }
          log(
            `Retrieved updated context: ${retrievedUpdatedContext.name} (${retrievedUpdatedContext.id})`
          );
          log(
            `Get Updated Context RequestId: ${
              getUpdatedContextResponse.requestId || "undefined"
            }`
          );

          // Verify the retrieved context has the updated name
          expect(retrievedUpdatedContext.name).toBe(updatedName);
          expect(retrievedUpdatedContext.id).toBe(originalContextID);

          // Step 7: List contexts again to verify the update is visible in the list
          log("Step 7: Listing contexts again to verify the update...");
          const listUpdatedContextsResponse = await agentBay.context.list();
          const updatedContexts = listUpdatedContextsResponse.contexts;
          log(
            `List Updated Contexts RequestId: ${
              listUpdatedContextsResponse.requestId || "undefined"
            }`
          );

          // Find the updated context in the list
          let foundInUpdatedList = false;
          for (const c of updatedContexts) {
            if (c.id === originalContextID) {
              foundInUpdatedList = true;
              expect(c.name).toBe(updatedName);
              break;
            }
          }
          expect(foundInUpdatedList).toBe(true);
          log("Successfully verified context update in the list");
        } finally {
          // Clean up the session
          log("Cleaning up: Deleting the session...");
          try {
            const deleteSessionResponse = await session.delete();
            log("Session successfully deleted");
            log(
              `Delete Session RequestId: ${
                deleteSessionResponse.requestId || "undefined"
              }`
            );
          } catch (error) {
            log(`Warning: Error deleting session: ${error}`);
          }
        }
      } finally {
        // Clean up the context
        log("Cleaning up: Deleting the context...");
        try {
          const deleteContextResponse = await agentBay.context.delete(context);
          log(`Context ${context.id} deleted successfully`);
          log(
            `Delete Context RequestId: ${
              deleteContextResponse.requestId || "undefined"
            }`
          );

          // Verify the context is actually deleted
          try {
            const getDeletedContextResponse = await agentBay.context.get(
              contextName
            );
            const deletedContext = getDeletedContextResponse.context;
            if (deletedContext && deletedContext.id === originalContextID) {
              log("Error: Context still exists after deletion");
            }
          } catch (error) {
            // This is expected - the context should not exist
            log("Context successfully deleted and no longer exists");
          }
        } catch (error) {
          log(`Warning: Error deleting context: ${error}`);
        }
      }
    });
  });
});
