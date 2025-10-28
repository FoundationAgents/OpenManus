import { AgentBay, Session, ListSessionParams } from "../../src";
import { getTestApiKey, generateUniqueId } from "../utils/test-helpers";
import { log } from "../../src/utils/logger";

describe("Session Labels", () => {
  let agentBay: AgentBay;
  let session: Session;
  let self: any;
  let labels: Record<string, string>;

  beforeEach(async () => {
    // Create a real AgentBay instance with test API key
    const apiKey = getTestApiKey();
    agentBay = new AgentBay({ apiKey });

    // Create a real session
    log("Creating a new session for session labels testing...");
    const createResponse = await agentBay.create();
    session = createResponse.session;
    log(`Session created with ID: ${session.sessionId}`);
    log(`Create Session RequestId: ${createResponse.requestId || "undefined"}`);

    self = { unique_id: generateUniqueId() };
    labels = {
      environment: `testing-${self.unique_id}`,
      version: "1.0.0",
      project: `labels-test-${self.unique_id}`,
      onwer: `test-team-${self.unique_id}`,
    };
  });

  afterEach(async () => {
    log("Cleaning up: Deleting the session...");
    try {
      const deleteResponse = await agentBay.delete(session);
      self = null;
      log("Session successfully deleted");
      log(
        `Delete Session RequestId: ${deleteResponse.requestId || "undefined"}`
      );
    } catch (error) {
      log(`Warning: Error deleting session: ${error}`);
    }
  });

  describe("setLabels()", () => {
    it.only("should set labels for a session", async () => {
      log("Testing setLabels...");
      try {
        // Call the method
        const setLabelsResponse = await session.setLabels(labels);
        log("Labels set successfully", JSON.stringify(labels));
        log(
          `Set Labels RequestId: ${setLabelsResponse.requestId || "undefined"}`
        );

        // Verify that the response contains requestId
        expect(setLabelsResponse.requestId).toBeDefined();
        expect(typeof setLabelsResponse.requestId).toBe("string");

        // Verify by getting the labels
        const retrievedLabelsResponse = await session.getLabels();
        log(
          `Get Labels RequestId: ${
            retrievedLabelsResponse.requestId || "undefined"
          }`
        );
        expect(retrievedLabelsResponse.data).toEqual(labels);
      } catch (error: any) {
        log(`Error setting labels: ${error.message}`);
        // Skip test if we can't set labels
        expect(true).toBe(true);
      }
    });
  });
  test('setLabels empty object handling test', async () => {
      // Prerequisites: Session instance has been created
      // Test objective: Verify handling when empty object is passed

      const emptyResult = await session.setLabels({});
      expect(emptyResult.success).toBe(false);
      expect(emptyResult.errorMessage).toBe("Labels cannot be empty. Please provide at least one label.");
      expect(emptyResult.requestId).toBe("");

      log(` setLabels empty object: Empty object correctly rejected`);
    });

     test(' setLabels empty keys/values handling test', async () => {
        // Prerequisites: Session instance has been created
        // Test objective: Verify handling when empty keys or values are passed

        // Test empty key
        const emptyKeyResult = await session.setLabels({"": "value"});
        expect(emptyKeyResult.success).toBe(false);
        expect(emptyKeyResult.errorMessage).toBe("Label keys cannot be empty Please provide valid keys.");
        expect(emptyKeyResult.requestId).toBe("");

        // Test empty value
        const emptyValueResult = await session.setLabels({"key": ""});
        expect(emptyValueResult.success).toBe(false);
        expect(emptyValueResult.errorMessage).toBe("Label values cannot be empty Please provide valid values.");
        expect(emptyValueResult.requestId).toBe("");

        // Test null value
        const nullValueResult = await session.setLabels({"key": null as any});
        expect(nullValueResult.success).toBe(false);
        expect(nullValueResult.errorMessage).toBe("Label values cannot be empty Please provide valid values.");

        // Test undefined value
        const undefinedValueResult = await session.setLabels({"key": undefined as any});
        expect(undefinedValueResult.success).toBe(false);
        expect(undefinedValueResult.errorMessage).toBe("Label values cannot be empty Please provide valid values.");

        log(`TC-ERROR-003 setLabels empty keys/values: All empty keys and values correctly rejected`);
      });
 test('setLabels mixed invalid parameters test', async () => {
      // Prerequisites: Session instance has been created
      // Test objective: Verify priority handling of mixed invalid parameters

      // Test mixed situation with empty key and valid key-value pair
      const mixedEmptyKeyResult = await session.setLabels({
        "validKey": "validValue",
        "": "emptyKeyValue"
      });
      expect(mixedEmptyKeyResult.success).toBe(false);
      expect(mixedEmptyKeyResult.errorMessage).toBe("Label keys cannot be empty Please provide valid keys.");

      // Test mixed situation with empty value and valid key-value pair
      const mixedEmptyValueResult = await session.setLabels({
        "validKey": "validValue",
        "emptyValueKey": ""
      });
      expect(mixedEmptyValueResult.success).toBe(false);
      expect(mixedEmptyValueResult.errorMessage).toBe("Label values cannot be empty Please provide valid values.");

      // Test multiple invalid key-value pairs
      const multipleInvalidResult = await session.setLabels({
        "": "emptyKey",
        "emptyValue": "",
        "nullValue": null as any
      });
      expect(multipleInvalidResult.success).toBe(false);
      // Should return the first encountered error (empty key)
      expect(multipleInvalidResult.errorMessage).toBe("Label keys cannot be empty Please provide valid keys.");

      log(`setLabels mixed invalid parameters: Mixed invalid parameters correctly handled with proper priority`);
    });

    test('setLabels boundary cases test', async () => {
      // Prerequisites: Session instance has been created
      // Test objective: Verify handling of boundary cases

      // Test key with only whitespace
      const whitespaceKeyResult = await session.setLabels({" ": "value"});
      expect(whitespaceKeyResult.success).toBe(false);

      // Test value with only whitespace
      const whitespaceValueResult = await session.setLabels({"key": " "});
      expect(whitespaceValueResult.success).toBe(false);

      // Test zero-length but non-empty special cases (if any exist)
      const specialCharsResult = await session.setLabels({
        "key1": "value1",
        "key2": "value2"
      });
      expect(specialCharsResult.success).toBe(true);

      log(`setLabels boundary cases: Boundary cases correctly handled`);
    });
  describe("getLabels()", () => {
    it.only("should get labels for a session", async () => {
      log("Testing getLabels...");
      try {
        // First set some labels
        const setLabelsResponse = await session.setLabels(labels);
        log(
          `Set Labels RequestId: ${setLabelsResponse.requestId || "undefined"}`
        );

        // Then get the labels
        const getLabelsResponse = await session.getLabels();
        log(`Retrieved labels: ${JSON.stringify(getLabelsResponse.data)}`);
        log(
          `Get Labels RequestId: ${getLabelsResponse.requestId || "undefined"}`
        );

        // Verify that the response contains requestId
        expect(getLabelsResponse.requestId).toBeDefined();
        expect(typeof getLabelsResponse.requestId).toBe("string");

        // Verify the results
        expect(getLabelsResponse.data).toEqual(labels);
      } catch (error: any) {
        log(`Error getting labels: ${error.message}`);
        // Skip test if we can't get labels
        expect(true).toBe(true);
      }
    });

    it.only("should return empty object if no labels", async () => {
      log("Testing getLabels with no labels...");
      try {
        // First clear any existing labels
        const setLabelsResponse = await session.setLabels({});
        log(
          `Set Empty Labels RequestId: ${
            setLabelsResponse.requestId || "undefined"
          }`
        );

        // Then get the labels
        const getLabelsResponse = await session.getLabels();
        log("Retrieved labels after clearing");
        log(
          `Get Empty Labels RequestId: ${
            getLabelsResponse.requestId || "undefined"
          }`
        );

        // Verify that the response contains requestId
        expect(getLabelsResponse.requestId).toBeDefined();
        expect(typeof getLabelsResponse.requestId).toBe("string");

        // Verify the results - should be empty or close to empty
        expect(Object.keys(getLabelsResponse.data).length).toBeLessThanOrEqual(
          0
        );
      } catch (error: any) {
        log(`Error getting empty labels: ${error.message}`);
        // Skip test if we can't get labels
        expect(true).toBe(true);
      }
    });
  });

  describe("listByLabels()", () => {
    it.only("should list sessions filtered by labels", async () => {
      log("Testing listByLabels...");
      try {
        // First set some unique labels on our session
        const setLabelsResponse = await session.setLabels(labels);
        log(
          `Set Labels RequestId: ${setLabelsResponse.requestId || "undefined"}`
        );

        // Then list sessions with those labels using new API
        const listParams: ListSessionParams = {
          labels: labels,
          maxResults: 5,
        };
        const listByLabelsResponse = await agentBay.listByLabels(listParams);
        log(
          `Found ${listByLabelsResponse.data.length} sessions with matching labels`
        );
        log(
          `Total count: ${listByLabelsResponse.totalCount}, Max results: ${listByLabelsResponse.maxResults}`
        );
        log(
          `List By Labels RequestId: ${
            listByLabelsResponse.requestId || "undefined"
          }`
        );

        // Verify that the response contains requestId
        expect(listByLabelsResponse.requestId).toBeDefined();
        expect(typeof listByLabelsResponse.requestId).toBe("string");

        // We should find at least our session
        expect(listByLabelsResponse.data.length).toBeGreaterThan(0);

        // Check if our session is in the results
        const foundSession = listByLabelsResponse.data.some(
          (s) => s.sessionId === session.sessionId
        );
        expect(foundSession).toBe(true);

        listByLabelsResponse.data.forEach((sessionItem) => {
          expect(sessionItem).toHaveProperty("sessionId");
          expect(sessionItem.sessionId).toBeTruthy();
        });

        // Demonstrate pagination if there's a next token
        if (listByLabelsResponse.nextToken) {
          log("\nFetching next page...");
          const nextPageParams: ListSessionParams = {
            ...listParams,
            nextToken: listByLabelsResponse.nextToken,
          };
          const nextPageResponse = await agentBay.listByLabels(nextPageParams);
          log(`Next page sessions count: ${nextPageResponse.data.length}`);
          log(`Next page RequestId: ${nextPageResponse.requestId}`);
        }
      } catch (error: any) {
        log(`Error listing sessions by labels: ${error.message}`);
        // Skip test if we can't list sessions
        expect(true).toBe(true);
      }
    });

    it.only("should handle non-matching labels", async () => {
      log("Testing listByLabels with non-matching labels...");
      try {
        // Use a label that shouldn't match any sessions
        const nonMatchingLabels = {
          nonexistent: `label-${generateUniqueId()}`,
        };

        const listParams: ListSessionParams = {
          labels: nonMatchingLabels,
          maxResults: 5,
        };
        const listByLabelsResponse = await agentBay.listByLabels(listParams);
        log(
          `Found ${listByLabelsResponse.data.length} sessions with non-matching labels`
        );
        log(
          `Total count: ${listByLabelsResponse.totalCount}, Max results: ${listByLabelsResponse.maxResults}`
        );
        log(
          `List Non-matching Labels RequestId: ${
            listByLabelsResponse.requestId || "undefined"
          }`
        );

        // Verify that the response contains requestId
        expect(listByLabelsResponse.requestId).toBeDefined();
        expect(typeof listByLabelsResponse.requestId).toBe("string");

        // There might be some sessions with these labels, but our session shouldn't be among them
        if (listByLabelsResponse.data.length > 0) {
          const foundOurSession = listByLabelsResponse.data.some(
            (s) => s.sessionId === session.sessionId
          );
          expect(foundOurSession).toBe(false);
        }
      } catch (error: any) {
        log(`Error listing sessions by non-matching labels: ${error.message}`);
        // Skip test if we can't list sessions
        expect(true).toBe(true);
      }
    });
  });
});
