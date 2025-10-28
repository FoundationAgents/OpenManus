import { AgentBay, Session } from "../../src";
import { getTestApiKey, wait } from "../utils/test-helpers";
import { log } from "../../src/utils/logger";

// Define test runner types if they're not available
declare function describe(name: string, fn: () => void): void;
declare function beforeEach(fn: () => void | Promise<void>): void;
declare function afterEach(fn: () => void | Promise<void>): void;
declare function it(name: string, fn: () => void | Promise<void>): void;
declare function expect(actual: any): any;

describe("Window Operations Integration", () => {
  let agentBay: AgentBay;
  let session: Session;

  beforeEach(async () => {
    const apiKey = getTestApiKey();
    agentBay = new AgentBay({ apiKey });

    // Create a session with linux_latest image
    log("Creating a new session for window operations testing...");
    const createResponse = await agentBay.create({ imageId: "linux_latest" });
    session = createResponse.session;
    log(`Session created with ID: ${session.sessionId}`);
    log(`Create Session RequestId: ${createResponse.requestId || "undefined"}`);
  });

  afterEach(async () => {
    // Clean up the session
    log("Cleaning up: Deleting the session...");
    try {
      if (session) {
        const deleteResponse = await agentBay.delete(session);
        log(
          `Delete Session RequestId: ${deleteResponse.requestId || "undefined"}`
        );
      }
    } catch (error) {
      log(`Warning: Error deleting session: ${error}`);
    }
  });

  describe("Window Operations", () => {
    it("should perform various window operations", async () => {
      // Set timeout to 2 minutes (120000 ms)
      jest.setTimeout(120000);
      // Test window operations
      if (session.window && session.application) {
        // Start Terminal application (using Linux default)
        log("Starting Terminal application...");
        const startCmd = "gnome-terminal";

        let processes: any[] = [];
        try {
          const startResponse = await session.application.startApp(
            startCmd,
            ""
          );
          processes = startResponse.data;
          log(
            `Terminal started successfully, returned ${processes.length} processes`
          );
          log(`Start App RequestId: ${startResponse.requestId || "undefined"}`);

          // Give Terminal some time to initialize
          await wait(5000);
        } catch (error) {
          log(`Note: Failed to start Terminal: ${error}`);
          log("Continuing with existing windows...");
        }

        // Clean up Terminal processes at the end if we successfully started them
        if (processes && processes.length > 0) {
          // Register cleanup function
          const cleanupTerminal = async () => {
            for (const process of processes) {
              if (process.pid > 0) {
                log(
                  `Attempting to stop Terminal process (PID: ${process.pid})...`
                );
                try {
                  const stopResponse = await session.application.stopAppByPID(
                    process.pid
                  );
                  log(
                    `Successfully stopped Terminal process (PID: ${process.pid})`
                  );
                  log(
                    `Stop App RequestId: ${
                      stopResponse.requestId || "undefined"
                    }`
                  );
                } catch (stopError) {
                  log(`Warning: Failed to stop Terminal process: ${stopError}`);
                }
              }
            }
          };

          // Make sure to call the cleanup function at the end of the test
          try {
            // Get a list of root windows
            const rootWindowsResponse = await session.window.listRootWindows();
            const rootWindows = rootWindowsResponse.windows;
            log(
              `List Root Windows RequestId: ${
                rootWindowsResponse.requestId || "undefined"
              }`
            );

            if (!rootWindows || rootWindows.length === 0) {
              log("No windows available for testing window operations");
              await cleanupTerminal();
              return;
            }

            // Try to find a Terminal window for testing
            let windowId = 0;
            let windowFound = false;
            for (const window of rootWindows) {
              if (
                window.pname?.toLowerCase().includes("terminal") ||
                window.pname?.toLowerCase().includes("gnome")
              ) {
                windowId = window.window_id;
                windowFound = true;
                log(
                  `Found Terminal window with ID ${windowId} for testing window operations`
                );
                break;
              }
            }

            // If no Terminal window found, use the first window
            if (!windowFound && rootWindows.length > 0) {
              windowId = rootWindows[0].window_id;
              log(
                `No Terminal window found, using window with ID ${windowId} for testing window operations`
              );
            }

            if (windowId === 0) {
              log("No suitable window found for testing");
              await cleanupTerminal();
              return;
            }

            // Test RestoreWindow
            log(`Restoring window with ID ${windowId}...`);
            try {
              const restoreResponse = await session.window.restoreWindow(
                windowId
              );
              log("Window restored successfully");
              log(
                `Restore Window RequestId: ${
                  restoreResponse.requestId || "undefined"
                }`
              );
            } catch (error) {
              log(`Note: RestoreWindow failed: ${error}`);
            }
            // Wait for 3 seconds to allow user to see the result
            await wait(3000);

            // Test ResizeWindow
            log(`Resizing window with ID ${windowId} to 800x600...`);
            try {
              const resizeResponse = await session.window.resizeWindow(
                windowId,
                800,
                600
              );
              log("Window resized successfully");
              log(
                `Resize Window RequestId: ${
                  resizeResponse.requestId || "undefined"
                }`
              );
            } catch (error) {
              log(`Note: ResizeWindow failed: ${error}`);
            }
            // Wait for 3 seconds to allow user to see the result
            await wait(3000);

            // Test MinimizeWindow
            log(`Minimizing window with ID ${windowId}...`);
            try {
              const minimizeResponse = await session.window.minimizeWindow(
                windowId
              );
              log("Window minimized successfully");
              log(
                `Minimize Window RequestId: ${
                  minimizeResponse.requestId || "undefined"
                }`
              );
            } catch (error) {
              log(`Note: MinimizeWindow failed: ${error}`);
            }
            // Wait for 3 seconds to allow user to see the result
            await wait(3000);

            // Test MaximizeWindow
            log(`Maximizing window with ID ${windowId}...`);
            try {
              const maximizeResponse = await session.window.maximizeWindow(
                windowId
              );
              log("Window maximized successfully");
              log(
                `Maximize Window RequestId: ${
                  maximizeResponse.requestId || "undefined"
                }`
              );
            } catch (error) {
              log(`Note: MaximizeWindow failed: ${error}`);
            }
            // Wait for 3 seconds to allow user to see the result
            await wait(3000);

            // Start a terminal
            log("Starting terminal...");
            let terminalCmd = "gnome-terminal";

            // Adjust command based on platform
            if (process.platform === "darwin") {
              terminalCmd = "open -a Terminal";
            } else if (process.platform === "win32") {
              terminalCmd = "start cmd";
            }

            let terminalProcesses: any[] = [];
            try {
              const terminalStartResponse = await session.application.startApp(
                terminalCmd,
                ""
              );
              terminalProcesses = terminalStartResponse.data;
              log(
                `Terminal started successfully, returned ${terminalProcesses.length} processes`
              );
              log(
                `Start Terminal RequestId: ${
                  terminalStartResponse.requestId || "undefined"
                }`
              );

              // Give terminal some time to initialize
              await wait(3000);

              // Clean up terminal processes at the end
              const cleanupTerminal = async () => {
                for (const process of terminalProcesses) {
                  if (process.pid > 0) {
                    log(
                      `Attempting to stop terminal process (PID: ${process.pid})...`
                    );
                    try {
                      const stopResponse =
                        await session.application.stopAppByPID(process.pid);
                      log(
                        `Successfully stopped terminal process (PID: ${process.pid})`
                      );
                      log(
                        `Stop Terminal RequestId: ${
                          stopResponse.requestId || "undefined"
                        }`
                      );
                    } catch (stopError) {
                      log(
                        `Warning: Failed to stop terminal process: ${stopError}`
                      );
                    }
                  }
                }
              };

              // Register cleanup for terminal
              try {
                // Activate the Terminal window again
                log(`Activating Terminal window with ID ${windowId} again...`);
                try {
                  const activateResponse = await session.window.activateWindow(
                    windowId
                  );
                  log("Window activated successfully");
                  log(
                    `Activate Window RequestId: ${
                      activateResponse.requestId || "undefined"
                    }`
                  );
                } catch (error) {
                  log(`Note: ActivateWindow failed: ${error}`);
                }
                // Wait for 3 seconds to allow user to see the result
                await wait(3000);

                // Test FullscreenWindow
                log(`Fullscreening window with ID ${windowId}...`);
                try {
                  const fullscreenResponse =
                    await session.window.fullscreenWindow(windowId);
                  log("Window fullscreened successfully");
                  log(
                    `Fullscreen Window RequestId: ${
                      fullscreenResponse.requestId || "undefined"
                    }`
                  );
                } catch (error) {
                  log(`Note: FullscreenWindow failed: ${error}`);
                }
                // Wait for 3 seconds to allow user to see the result
                await wait(3000);

                // Test CloseWindow
                log(`Closing window with ID ${windowId}...`);
                try {
                  const closeResponse = await session.window.closeWindow(
                    windowId
                  );
                  log("Window closed successfully");
                  log(
                    `Close Window RequestId: ${
                      closeResponse.requestId || "undefined"
                    }`
                  );
                } catch (error) {
                  log(`Note: CloseWindow failed: ${error}`);
                }
                // Wait for 3 seconds to allow user to see the result
                await wait(3000);
              } finally {
                await cleanupTerminal();
              }
            } catch (error) {
              log(`Note: Failed to start terminal: ${error}`);
            }
          } finally {
            await cleanupTerminal();
          }
        } else {
          log("No Terminal processes to test with, skipping window operations");
        }
      } else {
        log(
          "Note: Window or Application interface is nil, skipping window operations test"
        );
      }
    });
  });
});
