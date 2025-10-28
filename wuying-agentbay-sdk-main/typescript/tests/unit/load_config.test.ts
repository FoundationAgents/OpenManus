import { loadConfig, Config } from "../../src/config";
import * as fs from "fs";
import * as path from "path";
import * as os from "os";
import { log } from "../../src/utils/logger";

describe("Config", () => {
  let originalEnv: NodeJS.ProcessEnv;

  beforeEach(() => {
    originalEnv = process.env;
    // clear all environment variables
    process.env = {};

    // create a temporary directory
    const testDir = fs.mkdtempSync(path.join(os.tmpdir(), "config-test-"));
    process.chdir(testDir);
  });

  afterEach(() => {
    // restore environment variables
    process.env = originalEnv;
  });

  describe("test_load_from_passed_config", () => {
    it("should load configuration from passed Config object", () => {
      const customCfg: Config = {
        endpoint: "custom-endpoint",
        timeout_ms: 5000,
      };

      const result = loadConfig(customCfg);

      expect(result.endpoint).toBe("custom-endpoint");
      expect(result.timeout_ms).toBe(5000);
    });
  });

  describe("test_load_from_env_file", () => {
    it("should load configuration from .env file", () => {
      // create .env file and write test content
      const envFilePath = path.resolve(process.cwd(), ".env");
      fs.writeFileSync(
        envFilePath,
        "AGENTBAY_ENDPOINT=env-endpoint\n" +
          "AGENTBAY_TIMEOUT_MS=10000\n"
      );

      // validate file exists
      expect(fs.existsSync(envFilePath)).toBe(true);

      // clear environment variables
      process.env = {};

      // call loadConfig
      const result = loadConfig(undefined);

      // verify results
      expect(result.endpoint).toBe("env-endpoint");
      expect(result.timeout_ms).toBe(10000);
    });
  });

  describe("test_load_from_system_env_vars", () => {
    it("should load configuration from system environment variables", () => {
      // set environment variables
      process.env.AGENTBAY_ENDPOINT = "sys-endpoint";
      process.env.AGENTBAY_TIMEOUT_MS = "15000";

      // ensure no .env file exists
      const envFilePath = path.resolve(process.cwd(), ".env");
      if (fs.existsSync(envFilePath)) {
        fs.unlinkSync(envFilePath);
      }

      // call loadConfig
      const result = loadConfig(undefined);

      // verify results
      expect(result.endpoint).toBe("sys-endpoint");
      expect(result.timeout_ms).toBe(15000);
    });
  });

  describe("test_use_default_config_when_no_source_provided", () => {
    it("should use default configuration when no source is provided", () => {
      // clear all environment variables
      process.env = {};

      // make sure no .env file exists
      const envFilePath = path.resolve(process.cwd(), ".env");
      if (fs.existsSync(envFilePath)) {
        fs.unlinkSync(envFilePath);
      }

      // call loadConfig
      const result = loadConfig(undefined);

      // get default configuration
      const defaultCfg = {
        endpoint: "wuyingai.cn-shanghai.aliyuncs.com",
        timeout_ms: 60000,
      };

      // verify results
      expect(result.endpoint).toBe(defaultCfg.endpoint);
      expect(result.timeout_ms).toBe(defaultCfg.timeout_ms);
    });
  });

  describe("test_config_precedence_order", () => {
    it("should follow the correct precedence order for configuration sources", () => {
      // create .env file and write test content
      const envFilePath = path.resolve(process.cwd(), ".env");
      fs.writeFileSync(
        envFilePath,
        "AGENTBAY_ENDPOINT=env-endpoint\n" +
          "AGENTBAY_TIMEOUT_MS=10000\n"
      );

      // verify file exists
      expect(fs.existsSync(envFilePath)).toBe(true);

      // set environment variables
      process.env.AGENTBAY_ENDPOINT = "sys-endpoint";
      process.env.AGENTBAY_TIMEOUT_MS = "15000";

      // get default configuration
      const defaultCfg = {
        endpoint: "wuyingai.cn-shanghai.aliyuncs.com",
        timeout_ms: 60000,
      };

      // 1. explicit configuration should take precedence over all other sources
      const customCfg: Config = {
        endpoint: "explicit-endpoint",
        timeout_ms: 2000,
      };
      let result = loadConfig(customCfg);
      expect(result.endpoint).toBe("explicit-endpoint");
      expect(result.timeout_ms).toBe(2000);

      // 2. when no explicit configuration is provided, system environment variables should take precedence over .env file
      result = loadConfig(undefined);
      expect(result.endpoint).toBe("sys-endpoint");
      expect(result.timeout_ms).toBe(15000);

      // 3. after clearing environment variables, .env file should take precedence over default configuration
      delete process.env.AGENTBAY_ENDPOINT;
      delete process.env.AGENTBAY_TIMEOUT_MS;
      result = loadConfig(undefined);
      expect(result.endpoint).toBe("env-endpoint");
      expect(result.timeout_ms).toBe(10000);

      // 4. when no .env file exists, default configuration should be used
      fs.unlinkSync(envFilePath);
      // Clear any values that might have been loaded from .env file
      delete process.env.AGENTBAY_ENDPOINT;
      delete process.env.AGENTBAY_TIMEOUT_MS;
      result = loadConfig(undefined);
      expect(result.endpoint).toBe(defaultCfg.endpoint);
      expect(result.timeout_ms).toBe(defaultCfg.timeout_ms);
    });
  });
});
