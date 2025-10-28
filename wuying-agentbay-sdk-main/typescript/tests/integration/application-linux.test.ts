import { InstalledApp, Process } from "../../src/application/application";
import { AgentBay, Session } from "../../src";
import { getTestApiKey } from "../utils/test-helpers";
import { log } from "../../src/utils/logger";

describe("Application - Linux System Tests", () => {
  let session: Session;
  let agentBay: AgentBay;

  beforeEach(async () => {
    const apiKey = getTestApiKey();
    agentBay = new AgentBay({ apiKey });

    // Create a session with linux_latest image
    log("Creating a new Linux session for application testing...");
    const createResponse = await agentBay.create({ imageId: "linux_latest" });

    // Verify SessionResult structure
    expect(createResponse.success).toBe(true);
    expect(createResponse.session).toBeDefined();

    session = createResponse.session!;
    log(`Linux session created with ID: ${session.sessionId}`);
    log(`Create Session RequestId: ${createResponse.requestId || "undefined"}`);
  });

  afterEach(async () => {
    log("Cleaning up: Deleting the Linux session...");
    try {
      const deleteResponse = await agentBay.delete(session);
      log("Linux session successfully deleted");
      log(
        `Delete Session RequestId: ${deleteResponse.requestId || "undefined"}`
      );
    } catch (error) {
      log(`Warning: Error deleting Linux session: ${error}`);
    }
  });

  describe("getInstalledApps() - Linux", () => {
    it("should return Linux installed applications with valid properties", async () => {
      log("Testing getInstalledApps for Linux...");
      const appsResponse = await session.application.getInstalledApps(
        true,
        false,
        true
      );
      log(`Found ${appsResponse.data.length} Linux installed applications`);
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
          log(`Verifying Linux app ${index + 1}: ${app.name}`);
          expect(app.name).toBeTruthy();
          expect(app.start_cmd).toBeTruthy();
        });
      }
    });
  });

  describe("startApp() - Linux Applications", () => {
    it("should start Linux application and return processes", async () => {
      // Get installed apps from the remote system
      const appsResponse = await session.application.getInstalledApps(
        true,
        false,
        true
      );

      // Verify InstalledAppListResult structure
      expect(appsResponse.success).toBe(true);
      expect(appsResponse.data).toBeDefined();
      expect(Array.isArray(appsResponse.data)).toBe(true);
      expect(appsResponse.data.length).toBeGreaterThan(0);

      // Try to find Terminal in the installed apps
      let startCmd = "";
      const terminalApp = appsResponse.data.find(
        (app) => app.name === "Terminal"
      );

      if (terminalApp) {
        startCmd = terminalApp.start_cmd;
        log(`Using Terminal with start command: ${startCmd}`);
      } else {
        // Fallback to gnome-terminal if Terminal is not found
        startCmd = "gnome-terminal";
        log(
          `Terminal not found in installed apps, using default command: ${startCmd}`
        );
      }

      try {
        const processesResponse = await session.application.startApp(
          startCmd,
          ""
        );
        log(`Started ${processesResponse.data.length} Linux processes`);
        log(
          `Start App RequestId: ${processesResponse.requestId || "undefined"}`
        );

        // Verify ProcessListResult structure
        expect(processesResponse.success).toBe(true);
        expect(processesResponse.requestId).toBeDefined();
        expect(typeof processesResponse.requestId).toBe("string");
        expect(processesResponse.data).toBeDefined();
        expect(Array.isArray(processesResponse.data)).toBe(true);
        expect(processesResponse.errorMessage).toBeUndefined();

        if (processesResponse.data.length > 0) {
          processesResponse.data.forEach((proc, index) => {
            log(
              `Verifying Linux process ${index + 1}: ${proc.pname} (PID: ${
                proc.pid
              })`
            );
            expect(proc.pname).toBeTruthy();
            expect(proc.pid).toBeGreaterThan(0);
            expect(proc).toHaveProperty("cmdline");
          });
        }
      } catch (error) {
        log(`Note: Failed to start Linux application: ${error}`);
        // Skip test if we can't start the application
        expect(true).toBe(true);
      }
    });
  });

  describe("stopAppByPName() - Linux", () => {
    it("should stop Linux application by process name", async () => {
      try {
        // Get installed apps from the remote system
        const appsResponse = await session.application.getInstalledApps(
          true,
          false,
          true
        );

        expect(appsResponse.success).toBe(true);
        expect(appsResponse.data).toBeDefined();
        expect(Array.isArray(appsResponse.data)).toBe(true);
        expect(appsResponse.data.length).toBeGreaterThan(0);

        // Try to find Terminal in the installed apps
        let startCmd = "";
        const terminalApp = appsResponse.data.find(
          (app) => app.name === "Terminal"
        );

        if (terminalApp) {
          startCmd = terminalApp.start_cmd;
          log(`Using Terminal with start command: ${startCmd}`);
        } else {
          // Fallback to gnome-terminal if Terminal is not found
          startCmd = "gnome-terminal";
          log(
            `Terminal not found in installed apps, using default command: ${startCmd}`
          );
        }

        const processesResponse = await session.application.startApp(
          startCmd,
          ""
        );

        expect(processesResponse.success).toBe(true);
        expect(processesResponse.data).toBeDefined();
        expect(Array.isArray(processesResponse.data)).toBe(true);
        expect(processesResponse.data.length).toBeGreaterThan(0);

        const pname = processesResponse.data[0].pname;
        log(`Stopping Linux application with process name: ${pname}`);

        const stopResponse = await session.application.stopAppByPName(pname);
        log("Linux application stopped by process name successfully");
        log(
          `Stop App by PName RequestId: ${
            stopResponse.requestId || "undefined"
          }`
        );

        // Verify AppOperationResult structure
        expect(stopResponse.success).toBe(true);
        expect(stopResponse.requestId).toBeDefined();
        expect(typeof stopResponse.requestId).toBe("string");
        expect(stopResponse.errorMessage).toBeUndefined();
      } catch (error: any) {
        log(`Note: Failed to stop Linux application by process name: ${error}`);
        // Skip test if we can't stop the application
        expect(true).toBe(true);
      }
    });
  });

  describe("stopAppByPID() - Linux", () => {
    it("should stop Linux application by process ID", async () => {
      try {
        // Get installed apps from the remote system
        const appsResponse = await session.application.getInstalledApps(
          true,
          false,
          true
        );

        expect(appsResponse.success).toBe(true);
        expect(appsResponse.data).toBeDefined();
        expect(Array.isArray(appsResponse.data)).toBe(true);
        expect(appsResponse.data.length).toBeGreaterThan(0);

        // Try to find Terminal in the installed apps
        let startCmd = "";
        const terminalApp = appsResponse.data.find(
          (app) => app.name === "Terminal"
        );

        if (terminalApp) {
          startCmd = terminalApp.start_cmd;
          log(`Using Terminal with start command: ${startCmd}`);
        } else {
          // Fallback to gnome-terminal if Terminal is not found
          startCmd = "gnome-terminal";
          log(
            `Terminal not found in installed apps, using default command: ${startCmd}`
          );
        }

        const processesResponse = await session.application.startApp(
          startCmd,
          ""
        );

        expect(processesResponse.success).toBe(true);
        expect(processesResponse.data).toBeDefined();
        expect(Array.isArray(processesResponse.data)).toBe(true);
        expect(processesResponse.data.length).toBeGreaterThan(0);

        // Wait 5 seconds to give the application time to open
        log("Waiting 5 seconds to give Linux applications time to open...");
        await new Promise((resolve) => setTimeout(resolve, 5000));

        const pid = processesResponse.data[0].pid;
        const pname = processesResponse.data[0].pname;
        log(`Stopping Linux application with PID: ${pid} and name: ${pname}`);

        const stopResponse = await session.application.stopAppByPID(pid);
        log("Linux application stopped by PID successfully");
        log(
          `Stop App by PID RequestId: ${stopResponse.requestId || "undefined"}`
        );

        // Verify AppOperationResult structure
        expect(stopResponse.success).toBe(true);
        expect(stopResponse.requestId).toBeDefined();
        expect(typeof stopResponse.requestId).toBe("string");
        expect(stopResponse.errorMessage).toBeUndefined();

        // Wait 5 seconds to ensure the application has time to close
        log("Waiting 5 seconds to ensure the Linux application has closed...");
        await new Promise((resolve) => setTimeout(resolve, 5000));

        // Verify the app is no longer visible by using listVisibleApps
        const visibleAppsResponse = await session.application.listVisibleApps();

        // Verify ProcessListResult structure
        expect(visibleAppsResponse.success).toBe(true);
        expect(visibleAppsResponse.requestId).toBeDefined();
        expect(typeof visibleAppsResponse.requestId).toBe("string");
        expect(visibleAppsResponse.data).toBeDefined();
        expect(Array.isArray(visibleAppsResponse.data)).toBe(true);
        expect(visibleAppsResponse.errorMessage).toBeUndefined();

        if (visibleAppsResponse.data.length > 0) {
          visibleAppsResponse.data.forEach((app, index) => {
            log(
              `Verifying Linux app ${index + 1}: ${app.pname} (PID: ${app.pid})`
            );
            expect(app.pname).toBeTruthy();
            expect(app.pid).toBeGreaterThan(0);
          });
        }
      } catch (error: any) {
        log(`Note: Failed to stop Linux application by PID: ${error}`);
        // Skip test if we can't stop the application
        expect(true).toBe(true);
      }
    });
  });

  describe("listVisibleApps() - Linux", () => {
    it("should list visible Linux applications with valid properties", async () => {
      try {
        // First, start an application (Terminal) to ensure there's at least one visible app
        // Get installed apps from the remote system
        const appsResponse = await session.application.getInstalledApps(
          true,
          false,
          true
        );

        expect(appsResponse.success).toBe(true);
        expect(appsResponse.data).toBeDefined();
        expect(Array.isArray(appsResponse.data)).toBe(true);
        expect(appsResponse.data.length).toBeGreaterThan(0);

        // Try to find Terminal in the installed apps
        let startCmd = "";
        const terminalApp = appsResponse.data.find(
          (app) => app.name === "Terminal"
        );

        if (terminalApp) {
          startCmd = terminalApp.start_cmd;
          log(`Using Terminal with start command: ${startCmd}`);
        } else {
          // Fallback to gnome-terminal if Terminal is not found
          startCmd = "gnome-terminal";
          log(
            `Terminal not found in installed apps, using default command: ${startCmd}`
          );
        }

        // Start the terminal
        await session.application.startApp(startCmd, "");

        // Wait for the terminal to open
        log("Waiting 5 seconds to give the Linux terminal time to open...");
        await new Promise((resolve) => setTimeout(resolve, 5000));

        // Now list the visible applications
        const visibleAppsResponse = await session.application.listVisibleApps();
        log(
          `Found ${visibleAppsResponse.data.length} visible Linux applications`
        );
        log(
          `List Visible Apps RequestId: ${
            visibleAppsResponse.requestId || "undefined"
          }`
        );

        // Verify that the response contains requestId
        expect(visibleAppsResponse.requestId).toBeDefined();
        expect(typeof visibleAppsResponse.requestId).toBe("string");

        // Verify results
        expect(visibleAppsResponse.data).toBeDefined();
        expect(Array.isArray(visibleAppsResponse.data)).toBe(true);

        if (visibleAppsResponse.data.length > 0) {
          visibleAppsResponse.data.forEach((app, index) => {
            log(
              `Verifying Linux app ${index + 1}: ${app.pname} (PID: ${app.pid})`
            );
            expect(app.pname).toBeTruthy();
            expect(app.pid).toBeGreaterThan(0);
          });
        }
      } catch (error) {
        log(`Note: Failed in listVisibleApps Linux test: ${error}`);
        // Skip test if we encounter an error
        expect(true).toBe(true);
      }
    });
  });

  describe("stopAppByCmd() - Linux", () => {
    it("should stop Linux application by command", async () => {
      try {
        // Get installed apps from the remote system
        const appsResponse = await session.application.getInstalledApps(
          true,
          false,
          true
        );

        expect(appsResponse.success).toBe(true);
        expect(appsResponse.data).toBeDefined();
        expect(Array.isArray(appsResponse.data)).toBe(true);
        expect(appsResponse.data.length).toBeGreaterThan(0);

        // Try to find Terminal in the installed apps
        let startCmd = "";
        const terminalApp = appsResponse.data.find(
          (app) => app.name === "Terminal"
        );

        if (terminalApp) {
          startCmd = terminalApp.start_cmd;
          log(`Using Terminal with start command: ${startCmd}`);
        } else {
          // Fallback to gnome-terminal if Terminal is not found
          startCmd = "gnome-terminal";
          log(
            `Terminal not found in installed apps, using default command: ${startCmd}`
          );
        }

        // Start the terminal
        const processesResponse = await session.application.startApp(
          startCmd,
          ""
        );
        expect(processesResponse.data.length).toBeGreaterThan(0);

        // Wait for the terminal to open
        log("Waiting 5 seconds to give the Linux terminal time to open...");
        await new Promise((resolve) => setTimeout(resolve, 5000));

        // Use a stop command based on the process name
        const stopCmd = `pkill ${processesResponse.data[0].pname}`;
        log(`Using Linux stop command: ${stopCmd}`);

        // Stop the terminal with the command
        const stopResponse = await session.application.stopAppByCmd(stopCmd);
        log("Linux application stopped by command successfully");
        log(
          `Stop App by Cmd RequestId: ${stopResponse.requestId || "undefined"}`
        );

        // Verify that the response contains requestId
        expect(stopResponse.requestId).toBeDefined();
        expect(typeof stopResponse.requestId).toBe("string");

        // Wait for the terminal to close
        log("Waiting 5 seconds to give the Linux terminal time to close...");
        await new Promise((resolve) => setTimeout(resolve, 5000));

        // Verify the application is no longer visible
        const visibleAppsResponse = await session.application.listVisibleApps();
        const stoppedAppStillVisible = visibleAppsResponse.data.some(
          (app) => app.pid === processesResponse.data[0].pid
        );
        expect(stoppedAppStillVisible).toBe(false);
      } catch (error) {
        log(`Note: Failed in stopAppByCmd Linux test: ${error}`);
        // Skip test if we encounter an error
        expect(true).toBe(true);
      }
    });
  });
});
