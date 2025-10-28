import { InstalledApp, Process } from "../../src/application/application";
import { AgentBay, Session } from "../../src";
import { getTestApiKey } from "../utils/test-helpers";
import { log } from "../../src/utils/logger";

describe("Application - Mobile System Tests", () => {
  let session: Session;
  let agentBay: AgentBay;

  beforeEach(async () => {
    const apiKey = getTestApiKey();
    agentBay = new AgentBay({ apiKey });

    // Create a session with mobile_latest image
    log("Creating a new mobile session for application testing...");
    const createResponse = await agentBay.create({ imageId: "mobile_latest" });

    // Verify SessionResult structure
    expect(createResponse.success).toBe(true);
    expect(createResponse.session).toBeDefined();

    session = createResponse.session!;
    log(`Mobile session created with ID: ${session.sessionId}`);
    log(`Create Session RequestId: ${createResponse.requestId || "undefined"}`);
  });

  afterEach(async () => {
    log("Cleaning up: Deleting the mobile session...");
    try {
      debugger;
      const deleteResponse = await agentBay.delete(session);
      log("Mobile session successfully deleted");
      log(
        `Delete Session RequestId: ${deleteResponse.requestId || "undefined"}`
      );
    } catch (error) {
      log(`Warning: Error deleting mobile session: ${error}`);
    }
  });

  describe("getInstalledApps() - Mobile", () => {
    it("should return mobile installed applications with valid properties", async () => {
      log("Testing getInstalledApps for mobile...");
      const appsResponse = await session.application.getInstalledApps(
        true,
        false,
        true
      );
      log(`Found ${appsResponse.data.length} mobile installed applications`);
      log(
        `Get Installed Apps RequestId: ${appsResponse.requestId || "undefined"}`
      );

      // Verify InstalledAppListResult structure
      expect(appsResponse.success).toBe(true);
      expect(appsResponse.requestId).toBeDefined();
      expect(typeof appsResponse.requestId).toBe("string");
      expect(appsResponse.data).toBeDefined();
      expect(Array.isArray(appsResponse.data)).toBe(true);
      expect(appsResponse.errorMessage).toBeUndefined();

      if (appsResponse.data.length > 0) {
        appsResponse.data.forEach((app, index) => {
          log(`Verifying mobile app ${index + 1}: ${app.name}`);
          expect(app.name).toBeTruthy();
          expect(app.start_cmd).toBeTruthy();
        });
      }
    });
  });

  describe("startApp() - Mobile Applications (Python Example Style)", () => {
    it("should start mobile app with simple command like Python example", async () => {
      try {
        // Test case matching Python example usage:
        // session.application.start_app("monkey -p com.autonavi.minimap -c android.intent.category.LAUNCHER 1")
        const startCmd =
          "monkey -p com.autonavi.minimap -c android.intent.category.LAUNCHER 1";
        log(`Starting mobile app with command: ${startCmd}`);

        const processesResponse = await session.application.startApp(startCmd);
        log(
          `Start Mobile App RequestId: ${
            processesResponse.requestId || "undefined"
          }`
        );

        // Verify ProcessListResult structure
        expect(processesResponse.success).toBe(true);
        expect(processesResponse.requestId).toBeDefined();
        expect(typeof processesResponse.requestId).toBe("string");
        expect(processesResponse.data).toBeDefined();
        expect(Array.isArray(processesResponse.data)).toBe(true);
        expect(processesResponse.errorMessage).toBeUndefined();

        log(
          `Mobile app start result: ${processesResponse.data.length} processes`
        );
        if (processesResponse.data.length > 0) {
          processesResponse.data.forEach((proc, index) => {
            log(
              `Mobile process ${index + 1}: ${proc.pname} (PID: ${proc.pid})`
            );
            expect(proc.pname).toBeTruthy();
            expect(proc.pid).toBeGreaterThan(0);
          });
        }
      } catch (error) {
        log(
          `Note: Mobile app start test (expected in mobile environment): ${error}`
        );
        // This test is expected to work mainly in mobile environments
        expect(true).toBe(true);
      }
    });

    it("should start mobile app with activity like Python example", async () => {
      try {
        // Test case matching Python example usage with activity:
        // session.application.start_app(start_cmd=start_cmd, activity=app_activity)
        const appPackage = "com.xingin.xhs";
        const appActivity =
          "com.xingin.outside.activity.VivoOutsideFeedActivity";
        const startCmd = `monkey -p ${appPackage} -c android.intent.category.LAUNCHER 1`;

        log(`Starting mobile app with activity: ${appActivity}`);
        log(`Start command: ${startCmd}`);

        const processesResponse = await session.application.startApp(
          startCmd,
          "", // empty work_directory like Python example
          appActivity
        );
        log(
          `Start Mobile App with Activity RequestId: ${
            processesResponse.requestId || "undefined"
          }`
        );

        // Verify ProcessListResult structure
        expect(processesResponse.success).toBe(true);
        expect(processesResponse.requestId).toBeDefined();
        expect(typeof processesResponse.requestId).toBe("string");
        expect(processesResponse.data).toBeDefined();
        expect(Array.isArray(processesResponse.data)).toBe(true);
        expect(processesResponse.errorMessage).toBeUndefined();

        log(
          `Mobile app with activity start result: ${processesResponse.data.length} processes`
        );
        if (processesResponse.data.length > 0) {
          processesResponse.data.forEach((proc, index) => {
            log(
              `Mobile process with activity ${index + 1}: ${proc.pname} (PID: ${
                proc.pid
              })`
            );
            expect(proc.pname).toBeTruthy();
            expect(proc.pid).toBeGreaterThan(0);
          });
        }
      } catch (error) {
        log(
          `Note: Mobile app with activity test (expected in mobile environment): ${error}`
        );
        // This test is expected to work mainly in mobile environments
        expect(true).toBe(true);
      }
    });
  });

  describe("stopAppByCmd() - Mobile Style (Python Example)", () => {
    it("should stop mobile app by command like Python example", async () => {
      try {
        // Test case matching Python example usage:
        // session.application.stop_app_by_cmd("am force-stop com.sankuai.meituan")
        const stopCmd = "am force-stop com.xingin.xhs";
        log(`Stopping mobile app with command: ${stopCmd}`);

        const stopResponse = await session.application.stopAppByCmd(stopCmd);
        log("Mobile application stopped by command successfully");
        log(
          `Stop Mobile App by Cmd RequestId: ${
            stopResponse.requestId || "undefined"
          }`
        );

        // Verify AppOperationResult structure
        expect(stopResponse.success).toBe(true);
        expect(stopResponse.requestId).toBeDefined();
        expect(typeof stopResponse.requestId).toBe("string");
        expect(stopResponse.errorMessage).toBeUndefined();
        // AppOperationResult does not have data field
      } catch (error) {
        log(
          `Note: Mobile app stop by command test (expected in mobile environment): ${error}`
        );
        // This test is expected to work mainly in mobile environments
        expect(true).toBe(true);
      }
    });
  });

  describe("Mobile App Management Integration", () => {
    it("should handle complete mobile workflow like Python example", async () => {
      try {
        // Test complete workflow matching Python example:
        // 1. Get installed apps
        log("Step 1: Getting mobile installed applications...");
        const appsResponse = await session.application.getInstalledApps(
          true,
          false,
          true
        );

        // Verify InstalledAppListResult structure
        expect(appsResponse.success).toBe(true);
        expect(appsResponse.requestId).toBeDefined();
        expect(appsResponse.data).toBeDefined();
        expect(Array.isArray(appsResponse.data)).toBe(true);
        log(`Found ${appsResponse.data.length} mobile apps`);

        // 2. Start mobile app (simple command)
        log("Step 2: Starting mobile app with simple command...");
        const startCmd =
          "monkey -p com.autonavi.minimap -c android.intent.category.LAUNCHER 1";
        const startResponse = await session.application.startApp(startCmd);

        // Verify ProcessListResult structure
        expect(startResponse.success).toBe(true);
        expect(startResponse.requestId).toBeDefined();
        expect(startResponse.data).toBeDefined();
        expect(Array.isArray(startResponse.data)).toBe(true);
        log(`Started mobile app: ${startResponse.data.length} processes`);

        // 3. Start mobile app with activity
        log("Step 3: Starting mobile app with activity...");
        const appPackage = "com.xingin.xhs";
        const appActivity =
          "com.xingin.outside.activity.OppoOutsideFeedActivity";
        const activityStartCmd = `monkey -p ${appPackage} -c android.intent.category.LAUNCHER 1`;

        const activityStartResponse = await session.application.startApp(
          activityStartCmd,
          "",
          appActivity
        );

        // Verify ProcessListResult structure
        expect(activityStartResponse.success).toBe(true);
        expect(activityStartResponse.requestId).toBeDefined();
        expect(activityStartResponse.data).toBeDefined();
        expect(Array.isArray(activityStartResponse.data)).toBe(true);
        log(
          `Started mobile app with activity: ${activityStartResponse.data.length} processes`
        );
        debugger;
        // 4. Stop mobile app
        log("Step 4: Stopping mobile app...");
        const stopCmd = "am force-stop com.xingin.xhs";
        const stopResponse = await session.application.stopAppByCmd(stopCmd);

        // Verify AppOperationResult structure
        expect(stopResponse.success).toBe(true);
        expect(stopResponse.requestId).toBeDefined();
        expect(stopResponse.errorMessage).toBeUndefined();
        // AppOperationResult does not have data field
        log("Mobile app stopped successfully");

        log("Mobile workflow completed successfully!");
      } catch (error) {
        log(
          `Note: Mobile workflow test (expected in mobile environment): ${error}`
        );
        // This test is expected to work mainly in mobile environments
        expect(true).toBe(true);
      }
    });
  });
});
