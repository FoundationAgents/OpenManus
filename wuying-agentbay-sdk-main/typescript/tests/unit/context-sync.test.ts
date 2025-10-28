import {
  ContextSync,
  SyncPolicy,
  newSyncPolicy,
  newUploadPolicy,
  newDownloadPolicy,
  newDeletePolicy,
  newRecyclePolicy,
  newExtractPolicy,
  RecyclePolicy,
  UploadStrategy,
  DownloadStrategy,
  Lifecycle
} from "../../src/context-sync";
import { log } from "../../src/utils/logger";

describe("ContextSync Unit Tests", () => {
  describe("SyncPolicy Default Construction", () => {
    it("should create default SyncPolicy with correct values", () => {
      const policy = newSyncPolicy();


      // Verify the policy is not null
      expect(policy).toBeDefined();

      // Verify uploadPolicy
      expect(policy.uploadPolicy).toBeDefined();
      if (policy.uploadPolicy) {
        expect(policy.uploadPolicy.autoUpload).toBe(true);
        expect(policy.uploadPolicy.uploadStrategy).toBe(UploadStrategy.UploadBeforeResourceRelease);
      }

      // Verify downloadPolicy
      expect(policy.downloadPolicy).toBeDefined();
      if (policy.downloadPolicy) {
        expect(policy.downloadPolicy.autoDownload).toBe(true);
        expect(policy.downloadPolicy.downloadStrategy).toBe(DownloadStrategy.DownloadAsync);
      }

      // Verify deletePolicy
      expect(policy.deletePolicy).toBeDefined();
      if (policy.deletePolicy) {
        expect(policy.deletePolicy.syncLocalFile).toBe(true);
      }

      // Verify recyclePolicy
      expect(policy.recyclePolicy).toBeDefined();
      if (policy.recyclePolicy) {
        expect(policy.recyclePolicy.lifecycle).toBe(Lifecycle.Lifecycle_Forever);
        expect(policy.recyclePolicy.paths).toBeDefined();
        expect(policy.recyclePolicy.paths).toHaveLength(1);
        expect(policy.recyclePolicy.paths[0]).toBe("");
      }

      // Verify bwList
      expect(policy.bwList).toBeDefined();
      if (policy.bwList && policy.bwList.whiteLists) {
        expect(policy.bwList.whiteLists).toBeDefined();
        expect(policy.bwList.whiteLists).toHaveLength(1);
        
        const firstWhiteList = policy.bwList.whiteLists[0];
        expect(firstWhiteList.path).toBe("");
        expect(firstWhiteList.excludePaths).toBeDefined();
        if (firstWhiteList.excludePaths) {
          expect(firstWhiteList.excludePaths).toHaveLength(0);
        }
      }
      
    });

    it("should create default SyncPolicy that matches JSON requirements", () => {
      const policy = newSyncPolicy();

      // Convert to JSON and verify structure
      const jsonString = JSON.stringify(policy);
      const jsonObject = JSON.parse(jsonString);

      // Verify uploadPolicy in JSON
      expect(jsonObject.uploadPolicy).toBeDefined();
      expect(jsonObject.uploadPolicy.autoUpload).toBe(true);
      expect(jsonObject.uploadPolicy.uploadStrategy).toBe("UploadBeforeResourceRelease");

      // Verify downloadPolicy in JSON
      expect(jsonObject.downloadPolicy).toBeDefined();
      expect(jsonObject.downloadPolicy.autoDownload).toBe(true);
      expect(jsonObject.downloadPolicy.downloadStrategy).toBe("DownloadAsync");

      // Verify deletePolicy in JSON
      expect(jsonObject.deletePolicy).toBeDefined();
      expect(jsonObject.deletePolicy.syncLocalFile).toBe(true);

      // Verify recyclePolicy in JSON
      expect(jsonObject.recyclePolicy).toBeDefined();
      expect(jsonObject.recyclePolicy.lifecycle).toBe("Lifecycle_Forever");
      expect(jsonObject.recyclePolicy.paths).toBeDefined();
      expect(jsonObject.recyclePolicy.paths).toHaveLength(1);
      expect(jsonObject.recyclePolicy.paths[0]).toBe("");

      // Verify bwList in JSON
      expect(jsonObject.bwList).toBeDefined();
      expect(jsonObject.bwList.whiteLists).toBeDefined();
      expect(jsonObject.bwList.whiteLists).toHaveLength(1);
      expect(jsonObject.bwList.whiteLists[0].path).toBe("");
      // excludePaths should be present in JSON since it's an empty array
      expect(jsonObject.bwList.whiteLists[0].excludePaths).toBeDefined();
      expect(jsonObject.bwList.whiteLists[0].excludePaths).toHaveLength(0);

      // Verify syncPaths should not exist in JSON
      expect(jsonObject.syncPaths).toBeUndefined();

      // Log the generated JSON for verification
      log("Generated JSON:", jsonString);
    });

    it("should create individual policy components with correct defaults", () => {
      // Test UploadPolicy defaults
      const uploadPolicy = newUploadPolicy();
      expect(uploadPolicy.autoUpload).toBe(true);
      expect(uploadPolicy.uploadStrategy).toBe(UploadStrategy.UploadBeforeResourceRelease);

      // Test DownloadPolicy defaults
      const downloadPolicy = newDownloadPolicy();
      expect(downloadPolicy.autoDownload).toBe(true);
      expect(downloadPolicy.downloadStrategy).toBe(DownloadStrategy.DownloadAsync);

      // Test DeletePolicy defaults
      const deletePolicy = newDeletePolicy();
      expect(deletePolicy.syncLocalFile).toBe(true);
    });

    it("should create ContextSync with default policy", () => {
      const contextId = "test-context-123";
      const path = "/test/path";
      const policy = newSyncPolicy();

      const contextSync = new ContextSync(contextId, path, policy);

      expect(contextSync.contextId).toBe(contextId);
      expect(contextSync.path).toBe(path);
      expect(contextSync.policy).toBe(policy);
    });

    it("should allow chaining with withPolicy method", () => {
      const contextSync = new ContextSync("test-context", "/test/path");
      const policy = newSyncPolicy();

      const result = contextSync.withPolicy(policy);

      expect(result).toBe(contextSync);
      expect(contextSync.policy).toBe(policy);
    });

    it("should create RecyclePolicy with Lifecycle_1Day", () => {
      // Create a custom recycle policy with Lifecycle_1Day
      const customRecyclePolicy: RecyclePolicy = {
        lifecycle: Lifecycle.Lifecycle_1Day,
        paths: ["/custom/path"]
      };

      // Create a sync policy with the custom recycle policy
      const syncPolicy: SyncPolicy = {
        uploadPolicy: newUploadPolicy(),
        downloadPolicy: newDownloadPolicy(),
        deletePolicy: newDeletePolicy(),
        extractPolicy: newExtractPolicy(),
        recyclePolicy: customRecyclePolicy,
        bwList: {
          whiteLists: [
            {
              path: "",
              excludePaths: [],
            },
          ],
        },
      };

      // Verify the recycle policy
      expect(syncPolicy.recyclePolicy).toBeDefined();
      if (syncPolicy.recyclePolicy) {
        expect(syncPolicy.recyclePolicy.lifecycle).toBe(Lifecycle.Lifecycle_1Day);
        expect(syncPolicy.recyclePolicy.paths).toBeDefined();
        expect(syncPolicy.recyclePolicy.paths).toHaveLength(1);
        expect(syncPolicy.recyclePolicy.paths[0]).toBe("/custom/path");
      }

      // Test JSON serialization
      const jsonString = JSON.stringify(syncPolicy);
      const jsonObject = JSON.parse(jsonString);
      
      expect(jsonObject.recyclePolicy).toBeDefined();
      expect(jsonObject.recyclePolicy.lifecycle).toBe("Lifecycle_1Day");
      expect(jsonObject.recyclePolicy.paths).toHaveLength(1);
      expect(jsonObject.recyclePolicy.paths[0]).toBe("/custom/path");
      
    });

    it("should throw error when recyclePolicy path contains wildcard patterns", () => {
      // Create a recycle policy with invalid wildcard path
      const invalidRecyclePolicy: RecyclePolicy = {
        lifecycle: Lifecycle.Lifecycle_1Day,
        paths: ["/path/with/*"]
      };

      const syncPolicyWithInvalidPath: SyncPolicy = {
        uploadPolicy: newUploadPolicy(),
        downloadPolicy: newDownloadPolicy(),
        deletePolicy: newDeletePolicy(),
        extractPolicy: newExtractPolicy(),
        recyclePolicy: invalidRecyclePolicy,
        bwList: {
          whiteLists: [
            {
              path: "",
              excludePaths: [],
            },
          ],
        },
      };

      // Test that ContextSync constructor throws an error for invalid path
      expect(() => {
        new ContextSync("test-context", "/test/path", syncPolicyWithInvalidPath);
      }).toThrow("Wildcard patterns are not supported in path. Got: /path/with/*. Please use exact directory paths instead.");
    });
  });
});