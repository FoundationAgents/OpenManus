import {
  InstalledApp,
  Process,
  Application,
} from "../../src/application/application";
import * as sinon from "sinon";

const mockInstalledAppsData: InstalledApp[] = [
  {
    name: "Meituan",
    start_cmd:
      "monkey -p com.sankuai.meituan -c android.intent.category.LAUNCHER 1",
    stop_cmd: "am force-stop com.sankuai.meituan",
    work_directory: "",
  },
  {
    name: "Xiaohongshu",
    start_cmd: "monkey -p com.xingin.xhs -c android.intent.category.LAUNCHER 1",
    stop_cmd: "am force-stop com.xingin.xhs",
    work_directory: "",
  },
  {
    name: "Amap",
    start_cmd:
      "monkey -p com.autonavi.minimap -c android.intent.category.LAUNCHER 1",
    stop_cmd: "am force-stop com.autonavi.minimap",
    work_directory: "",
  },
];

const mockProcessData: Process[] = [
  {
    pname: "com.autonavi.minimap",
    pid: 12345,
    cmdline:
      "monkey -p com.autonavi.minimap -c android.intent.category.LAUNCHER 1",
  },
];

const mockVisibleAppsData: Process[] = [
  {
    pname: "com.autonavi.minimap",
    pid: 12345,
    cmdline: "cmd1",
  },
  {
    pname: "com.xingin.xhs",
    pid: 23456,
    cmdline: "cmd2",
  },
];

describe("ApplicationApi", () => {
  let mockApplication: Application;
  let mockSession: any;
  let sandbox: sinon.SinonSandbox;
  let callMcpToolStub: sinon.SinonStub;

  beforeEach(() => {
    sandbox = sinon.createSandbox();

    mockSession = {
      getAPIKey: sandbox.stub().returns("test-api-key"),
      getClient: sandbox.stub(),
      getSessionId: sandbox.stub().returns("test-session-id"),
      callMcpTool: sandbox.stub(),
    };

    mockApplication = new Application(mockSession);
    callMcpToolStub = mockSession.callMcpTool;
  });

  afterEach(() => {
    sandbox.restore();
  });

  describe("test_get_installed_apps_success", () => {
    it("should get installed apps successfully", async () => {
      callMcpToolStub.resolves({
        success: true,
        data: JSON.stringify(mockInstalledAppsData),
        requestId: "test-request-id",
      });

      const result = await mockApplication.getInstalledApps();

      // Verify InstalledAppListResult structure
      expect(result.success).toBe(true);
      expect(result.requestId).toBe("test-request-id");
      expect(result.data).toHaveLength(3);
      expect(result.errorMessage).toBeUndefined();

      expect(result.data[0]).toBeInstanceOf(Object);
      expect(result.data[0].name).toBe("Meituan");
      expect(result.data[1].name).toBe("Xiaohongshu");
      expect(result.data[2].name).toBe("Amap");

      expect(callMcpToolStub.calledOnce).toBe(true);
      const callArgs = callMcpToolStub.getCall(0).args;
      expect(callArgs[0]).toBe("get_installed_apps");
      expect(callArgs[1]).toEqual({
        start_menu: false,
        desktop: true,
        ignore_system_apps: true,
      });
    });
  });

  describe("test_get_installed_apps_failure", () => {
    it("should handle get installed apps failure", async () => {
      callMcpToolStub.resolves({
        success: false,
        data: "",
        errorMessage: "Failed to get installed apps",
        requestId: "test-request-id",
      });

      const result = await mockApplication.getInstalledApps();

      // Verify error result structure
      expect(result.success).toBe(false);
      expect(result.requestId).toBe("test-request-id");
      expect(result.data).toHaveLength(0);
      expect(result.errorMessage).toBe("Failed to get installed apps");
    });
  });

  describe("test_start_app_success", () => {
    it("should start app successfully", async () => {
      const mockXhsProcessData: Process[] = [
        {
          pname: "com.xingin.xhs",
          pid: 23456,
          cmdline:
            "monkey -p com.xingin.xhs -c android.intent.category.LAUNCHER 1",
        },
      ];

      callMcpToolStub.resolves({
        success: true,
        data: JSON.stringify(mockXhsProcessData),
        errorMessage: "",
        requestId: "test-request-456",
      });

      const result = await mockApplication.startApp(
        "monkey -p com.xingin.xhs -c android.intent.category.LAUNCHER 1",
        "/storage/emulated/0",
        "com.xingin.xhs/.MainActivity"
      );

      // Verify ProcessListResult structure
      expect(result.success).toBe(true);
      expect(result.requestId).toBe("test-request-456");
      expect(result.data).toHaveLength(1);
      expect(result.errorMessage).toBeUndefined();

      expect(result.data[0].pname).toBe("com.xingin.xhs");
      expect(result.data[0].pid).toBe(23456);

      // Verify all parameters were passed correctly
      expect(callMcpToolStub.calledOnce).toBe(true);
      const callArgs = callMcpToolStub.getCall(0).args;
      expect(callArgs[0]).toBe("start_app");
      expect(callArgs[1]).toEqual({
        start_cmd:
          "monkey -p com.xingin.xhs -c android.intent.category.LAUNCHER 1",
        work_directory: "/storage/emulated/0",
        activity: "com.xingin.xhs/.MainActivity",
      });
    });
  });

  describe("test_start_app_failure", () => {
    it("should handle start app failure", async () => {
      callMcpToolStub.resolves({
        success: false,
        data: "",
        errorMessage: "Failed to start app",
        requestId: "test-request-id",
      });

      const result = await mockApplication.startApp(
        "monkey -p com.xingin.xhs -c android.intent.category.LAUNCHER 1"
      );

      // Verify error result structure
      expect(result.success).toBe(false);
      expect(result.requestId).toBe("test-request-id");
      expect(result.data).toHaveLength(0);
      expect(result.errorMessage).toBe("Failed to start app");
    });
  });

  describe("test_start_app_with_activity_success", () => {
    it("should start app with activity successfully", async () => {
      callMcpToolStub.resolves({
        success: true,
        data: JSON.stringify(mockProcessData),
        errorMessage: "",
        requestId: "test-request-id",
      });

      const result = await mockApplication.startApp(
        "monkey -p com.autonavi.minimap -c android.intent.category.LAUNCHER 1",
        "",
        "com.autonavi.minimap/.MainActivity"
      );

      // Verify ProcessListResult structure
      expect(result.success).toBe(true);
      expect(result.requestId).toBe("test-request-id");
      expect(result.data).toHaveLength(1);
      expect(result.errorMessage).toBeUndefined();

      expect(result.data[0].pname).toBe("com.autonavi.minimap");
      expect(result.data[0].pid).toBe(12345);

      // Verify all parameters were passed correctly
      expect(callMcpToolStub.calledOnce).toBe(true);
      const callArgs = callMcpToolStub.getCall(0).args;
      expect(callArgs[0]).toBe("start_app");
      expect(callArgs[1]).toEqual({
        start_cmd:
          "monkey -p com.autonavi.minimap -c android.intent.category.LAUNCHER 1",
        work_directory: "",
        activity: "com.autonavi.minimap/.MainActivity",
      });
    });
  });

  describe("test_start_app_with_activity_and_work_directory", () => {
    it("should start app with activity and work directory successfully", async () => {
      const mockXhsProcessData: Process[] = [
        {
          pname: "com.xingin.xhs",
          pid: 23456,
          cmdline:
            "monkey -p com.xingin.xhs -c android.intent.category.LAUNCHER 1",
        },
      ];

      callMcpToolStub.resolves({
        success: true,
        data: JSON.stringify(mockXhsProcessData),
        errorMessage: "",
        requestId: "test-request-456",
      });

      const result = await mockApplication.startApp(
        "monkey -p com.xingin.xhs -c android.intent.category.LAUNCHER 1",
        "/storage/emulated/0",
        "com.xingin.xhs/.MainActivity"
      );

      // Verify ProcessListResult structure
      expect(result.success).toBe(true);
      expect(result.requestId).toBe("test-request-456");
      expect(result.data).toHaveLength(1);
      expect(result.errorMessage).toBeUndefined();

      expect(result.data[0].pname).toBe("com.xingin.xhs");
      expect(result.data[0].pid).toBe(23456);

      // Verify all parameters were passed correctly
      expect(callMcpToolStub.calledOnce).toBe(true);
      const callArgs = callMcpToolStub.getCall(0).args;
      expect(callArgs[0]).toBe("start_app");
      expect(callArgs[1]).toEqual({
        start_cmd:
          "monkey -p com.xingin.xhs -c android.intent.category.LAUNCHER 1",
        work_directory: "/storage/emulated/0",
        activity: "com.xingin.xhs/.MainActivity",
      });
    });
  });

  describe("test_stop_app_by_cmd_success", () => {
    it("should stop app by command successfully", async () => {
      callMcpToolStub.resolves({
        success: true,
        data: "",
        requestId: "test-request-id",
      });

      const result = await mockApplication.stopAppByCmd(
        "am force-stop com.autonavi.minimap"
      );

      // Verify AppOperationResult structure
      expect(result.success).toBe(true);
      expect(result.requestId).toBe("test-request-id");
      expect(result.errorMessage).toBeUndefined();

      expect(callMcpToolStub.calledOnce).toBe(true);
    });
  });

  describe("test_stop_app_by_cmd_failure", () => {
    it("should handle stop app by command failure", async () => {
      callMcpToolStub.resolves({
        success: false,
        data: "",
        errorMessage: "Failed to stop app",
        requestId: "test-request-id",
      });

      const result = await mockApplication.stopAppByCmd(
        "am force-stop com.autonavi.minimap"
      );

      // Verify error result structure
      expect(result.success).toBe(false);
      expect(result.requestId).toBe("test-request-id");
      expect(result.errorMessage).toBe("Failed to stop app");
    });
  });

  describe("test_stop_app_by_pname_success", () => {
    it("should stop app by package name successfully", async () => {
      callMcpToolStub.resolves({
        success: true,
        data: "",
        errorMessage: "",
        requestId: "test-request-id",
      });

      const result = await mockApplication.stopAppByPName(
        "com.autonavi.minimap"
      );

      // Verify AppOperationResult structure
      expect(result.success).toBe(true);
      expect(result.requestId).toBe("test-request-id");
      expect(result.errorMessage).toBeUndefined();

      expect(callMcpToolStub.calledOnce).toBe(true);
    });
  });

  describe("test_stop_app_by_pname_failure", () => {
    it("should handle stop app by package name failure", async () => {
      callMcpToolStub.resolves({
        success: false,
        data: "",
        errorMessage: "Failed to stop app by pname",
        requestId: "test-request-id",
      });

      const result = await mockApplication.stopAppByPName(
        "com.autonavi.minimap"
      );

      // Verify error result structure
      expect(result.success).toBe(false);
      expect(result.requestId).toBe("test-request-id");
      expect(result.errorMessage).toContain("Failed to stop app by pname");
    });
  });

  describe("test_stop_app_by_pid_success", () => {
    it("should stop app by PID successfully", async () => {
      callMcpToolStub.resolves({
        success: true,
        data: "",
        errorMessage: "",
        requestId: "test-request-id",
      });

      const result = await mockApplication.stopAppByPID(12345);

      // Verify AppOperationResult structure
      expect(result.success).toBe(true);
      expect(result.requestId).toBe("test-request-id");
      expect(result.errorMessage).toBeUndefined();

      expect(callMcpToolStub.calledOnce).toBe(true);
    });
  });

  describe("test_stop_app_by_pid_failure", () => {
    it("should handle stop app by PID failure", async () => {
      callMcpToolStub.resolves({
        success: false,
        data: "",
        errorMessage: "Failed to stop app by pid",
        requestId: "test-request-id",
      });

      const result = await mockApplication.stopAppByPID(12345);

      // Verify error result structure
      expect(result.success).toBe(false);
      expect(result.requestId).toBe("test-request-id");
      expect(result.errorMessage).toContain("Failed to stop app by pid");
    });
  });

  describe("test_list_visible_apps_success", () => {
    it("should list visible apps successfully", async () => {
      callMcpToolStub.resolves({
        success: true,
        data: JSON.stringify(mockVisibleAppsData),
        errorMessage: "",
        requestId: "test-request-id",
      });

      const result = await mockApplication.listVisibleApps();

      // Verify ProcessListResult structure
      expect(result.success).toBe(true);
      expect(result.requestId).toBe("test-request-id");
      expect(result.data).toHaveLength(2);
      expect(result.errorMessage).toBeUndefined();

      expect(result.data[0].pname).toBe("com.autonavi.minimap");
      expect(result.data[0].pid).toBe(12345);
      expect(result.data[1].pname).toBe("com.xingin.xhs");
      expect(result.data[1].pid).toBe(23456);

      expect(callMcpToolStub.calledOnce).toBe(true);
    });
  });

  describe("test_list_visible_apps_failure", () => {
    it("should handle list visible apps failure", async () => {
      callMcpToolStub.resolves({
        success: false,
        data: "",
        errorMessage: "Failed to list visible apps",
        requestId: "test-request-id",
      });

      const result = await mockApplication.listVisibleApps();

      // Verify error result structure
      expect(result.success).toBe(false);
      expect(result.requestId).toBe("test-request-id");
      expect(result.data).toHaveLength(0);
      expect(result.errorMessage).toContain("Failed to list visible apps");
    });
  });
});
