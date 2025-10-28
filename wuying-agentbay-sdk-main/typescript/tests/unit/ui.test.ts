import { UI, KeyCode } from "../../src/ui/ui";
import * as sinon from "sinon";

describe("TestUIApi", () => {
  let mockUI: UI;
  let mockSession: any;
  let sandbox: sinon.SinonSandbox;
  let callMcpToolStub: sinon.SinonStub;

  beforeEach(() => {
    sandbox = sinon.createSandbox();
    mockSession = {
      getAPIKey: sandbox.stub().returns("test-api-key"),
      getSessionId: sandbox.stub().returns("test-session-id"),
      getClient: sandbox.stub().returns({
        callMcpTool: sandbox.stub(),
      }),
      callMcpTool: sandbox.stub(),
    };
    mockUI = new UI(mockSession);
    callMcpToolStub = mockSession.callMcpTool;
  });

  afterEach(() => {
    sandbox.restore();
  });

  describe("test_get_clickable_ui_elements_success", () => {
    it("should get clickable UI elements successfully", async () => {
      const mockElements = [
        {
          bounds: "48,90,1032,630",
          className: "LinearLayout",
          text: "digital_widget",
          type: "clickable",
          resourceId: "com.example:id/widget",
          index: 0,
          isParent: false,
        },
      ];

      callMcpToolStub.resolves({
        success: true,
        data: JSON.stringify(mockElements),
        requestId: "test-request-id",
      });

      const result = await mockUI.getClickableUIElements();

      // Verify UIElementListResult structure
      expect(result.success).toBe(true);
      expect(result.requestId).toBe("test-request-id");
      expect(result.elements).toHaveLength(1);
      expect(result.errorMessage).toBeUndefined();

      // Verify element structure
      expect(result.elements[0].bounds).toBe("48,90,1032,630");
      expect(result.elements[0].className).toBe("LinearLayout");
      expect(result.elements[0].text).toBe("digital_widget");

      expect(callMcpToolStub.calledOnce).toBe(true);
    });
  });

  describe("test_get_clickable_ui_elements_failure", () => {
    it("should handle get clickable UI elements failure", async () => {
      callMcpToolStub.resolves({
        success: false,
        data: "",
        errorMessage: "Failed to get clickable UI elements",
        requestId: "test-request-id",
      });

      const result = await mockUI.getClickableUIElements();

      // Verify error result structure
      expect(result.success).toBe(false);
      expect(result.requestId).toBe("test-request-id");
      expect(result.elements).toHaveLength(0);
      expect(result.errorMessage).toBe("Failed to get clickable UI elements");
    });
  });

  describe("test_send_key_success", () => {
    it("should send key successfully", async () => {
      callMcpToolStub.resolves({
        success: true,
        data: "",
        requestId: "key-request-id",
      });

      const result = await mockUI.sendKey(KeyCode.HOME);

      // Verify BoolResult structure
      expect(result.success).toBe(true);
      expect(result.requestId).toBe("key-request-id");
      expect(result.data).toBe(true);
      expect(result.errorMessage).toBeUndefined();

      expect(callMcpToolStub.calledOnce).toBe(true);
      const callArgs = callMcpToolStub.getCall(0).args;
      expect(callArgs[0]).toBe("send_key");
      expect(callArgs[1]).toEqual({ key: KeyCode.HOME });
    });
  });

  describe("test_send_key_failure", () => {
    it("should handle send key failure", async () => {
      callMcpToolStub.resolves({
        success: false,
        data: "",
        errorMessage: "Failed to send key",
        requestId: "key-request-id",
      });

      const result = await mockUI.sendKey(KeyCode.HOME);

      // Verify error result structure
      expect(result.success).toBe(false);
      expect(result.requestId).toBe("key-request-id");
      expect(result.data).toBe(false);
      expect(result.errorMessage).toBe("Failed to send key");
    });
  });

  describe("test_swipe_success", () => {
    it("should perform swipe successfully", async () => {
      callMcpToolStub.resolves({
        success: true,
        data: "",
        requestId: "swipe-request-id",
      });

      const result = await mockUI.swipe(100, 200, 300, 400, 500);

      // Verify BoolResult structure
      expect(result.success).toBe(true);
      expect(result.requestId).toBe("swipe-request-id");
      expect(result.data).toBe(true);
      expect(result.errorMessage).toBeUndefined();

      expect(callMcpToolStub.calledOnce).toBe(true);
      const callArgs = callMcpToolStub.getCall(0).args;
      expect(callArgs[0]).toBe("swipe");
      expect(callArgs[1]).toEqual({
        start_x: 100,
        start_y: 200,
        end_x: 300,
        end_y: 400,
        duration_ms: 500,
      });
    });
  });

  describe("test_swipe_failure", () => {
    it("should handle swipe failure", async () => {
      callMcpToolStub.resolves({
        success: false,
        data: "",
        errorMessage: "Failed to perform swipe",
        requestId: "swipe-request-id",
      });

      const result = await mockUI.swipe(100, 200, 300, 400, 500);

      // Verify error result structure
      expect(result.success).toBe(false);
      expect(result.requestId).toBe("swipe-request-id");
      expect(result.data).toBe(false);
      expect(result.errorMessage).toBe("Failed to perform swipe");
    });
  });

  describe("test_click_success", () => {
    it("should perform click successfully", async () => {
      callMcpToolStub.resolves({
        success: true,
        data: "",
        requestId: "click-request-id",
      });

      const result = await mockUI.click(150, 250);

      // Verify BoolResult structure
      expect(result.success).toBe(true);
      expect(result.requestId).toBe("click-request-id");
      expect(result.data).toBe(true);
      expect(result.errorMessage).toBeUndefined();

      expect(callMcpToolStub.calledOnce).toBe(true);
      const callArgs = callMcpToolStub.getCall(0).args;
      expect(callArgs[0]).toBe("click");
      expect(callArgs[1]).toEqual({ x: 150, y: 250, button: "left" });
    });
  });

  describe("test_click_failure", () => {
    it("should handle click failure", async () => {
      callMcpToolStub.resolves({
        success: false,
        data: "",
        errorMessage: "Failed to perform click",
        requestId: "click-request-id",
      });

      const result = await mockUI.click(150, 250);

      // Verify error result structure
      expect(result.success).toBe(false);
      expect(result.requestId).toBe("click-request-id");
      expect(result.data).toBe(false);
      expect(result.errorMessage).toBe("Failed to perform click");
    });
  });

  describe("test_input_text_success", () => {
    it("should input text successfully", async () => {
      callMcpToolStub.resolves({
        success: true,
        data: "",
        requestId: "input-text-request-id",
      });

      const result = await mockUI.inputText("Hello World");

      // Verify BoolResult structure
      expect(result.success).toBe(true);
      expect(result.requestId).toBe("input-text-request-id");
      expect(result.data).toBe(true);
      expect(result.errorMessage).toBeUndefined();

      expect(callMcpToolStub.calledOnce).toBe(true);
      const callArgs = callMcpToolStub.getCall(0).args;
      expect(callArgs[0]).toBe("input_text");
      expect(callArgs[1]).toEqual({ text: "Hello World" });
    });
  });

  describe("test_input_text_failure", () => {
    it("should handle input text failure", async () => {
      callMcpToolStub.resolves({
        success: false,
        data: "",
        errorMessage: "Failed to input text",
        requestId: "input-text-request-id",
      });

      const result = await mockUI.inputText("Hello World");

      // Verify error result structure
      expect(result.success).toBe(false);
      expect(result.requestId).toBe("input-text-request-id");
      expect(result.data).toBe(false);
      expect(result.errorMessage).toBe("Failed to input text");
    });
  });

  describe("test_get_all_ui_elements_success", () => {
    it("should get all UI elements successfully", async () => {
      const mockElements = [
        {
          bounds: "0,0,1080,1920",
          className: "FrameLayout",
          text: "",
          type: "container",
          resourceId: "android:id/content",
          index: 0,
          isParent: true,
        },
      ];

      callMcpToolStub.resolves({
        success: true,
        data: JSON.stringify(mockElements),
        requestId: "get-all-elements-request-id",
      });

      const result = await mockUI.getAllUIElements();

      // Verify UIElementListResult structure
      expect(result.success).toBe(true);
      expect(result.requestId).toBe("get-all-elements-request-id");
      expect(result.elements).toHaveLength(1);
      expect(result.errorMessage).toBeUndefined();

      // Verify element structure
      expect(result.elements[0].bounds).toBe("0,0,1080,1920");
      expect(result.elements[0].className).toBe("FrameLayout");
      expect(result.elements[0].isParent).toBe(true);

      expect(callMcpToolStub.calledOnce).toBe(true);
    });
  });

  describe("test_get_all_ui_elements_failure", () => {
    it("should handle get all UI elements failure", async () => {
      callMcpToolStub.resolves({
        success: false,
        data: "",
        errorMessage: "Failed to get all UI elements",
        requestId: "get-all-elements-request-id",
      });

      const result = await mockUI.getAllUIElements();

      // Verify error result structure
      expect(result.success).toBe(false);
      expect(result.requestId).toBe("get-all-elements-request-id");
      expect(result.elements).toHaveLength(0);
      expect(result.errorMessage).toBe("Failed to get all UI elements");
    });
  });

  describe("test_screenshot_success", () => {
    it("should take screenshot successfully", async () => {
      const OSS_URL = "https://example.com/screenshot.png";
      
      callMcpToolStub.resolves({
        success: true,
        data: OSS_URL,
        requestId: "screenshot-request-id",
      });

      const result = await mockUI.screenshot();

      // Verify OperationResult structure
      expect(result.success).toBe(true);
      expect(result.requestId).toBe("screenshot-request-id");
      expect(result.data).toBe(OSS_URL);
      expect(result.errorMessage).toBeUndefined();

      expect(callMcpToolStub.calledOnce).toBe(true);
      const callArgs = callMcpToolStub.getCall(0).args;
      expect(callArgs[0]).toBe("system_screenshot");
    });
  });

  describe("test_screenshot_failure", () => {
    it("should handle screenshot failure", async () => {
      callMcpToolStub.resolves({
        success: false,
        data: "",
        errorMessage: "Failed to take screenshot",
        requestId: "screenshot-request-id",
      });

      const result = await mockUI.screenshot();

      // Verify error result structure
      expect(result.success).toBe(false);
      expect(result.requestId).toBe("screenshot-request-id");
      expect(result.data).toBe("");
      expect(result.errorMessage).toBe("Failed to take screenshot");
    });
  });

  describe("test_screenshot_exception_handling", () => {
    it("should handle screenshot exception", async () => {
      callMcpToolStub.rejects(new Error("Network error"));

      const result = await mockUI.screenshot();

      // Verify error result structure
      expect(result.success).toBe(false);
      expect(result.requestId).toBe("");
      expect(result.data).toBe("");
      expect(result.errorMessage).toContain("Failed to take screenshot");
      expect(result.errorMessage).toContain("Network error");
    });
  });
});
