import * as fs from "fs";
import * as path from "path";
import * as dotenv from "dotenv";
import { log } from "./utils/logger";
interface Config {
  endpoint: string;
  timeout_ms: number;
}

/**
 * Browser data path constant
 */
export const BROWSER_DATA_PATH = "/tmp/agentbay_browser";

/**
 * Returns the default configuration
 */
export function defaultConfig(): Config {
  return {
    endpoint: "wuyingai.cn-shanghai.aliyuncs.com",
    timeout_ms: 60000,
  };
}

/**
 * Find .env file by searching upward from start_path.
 * 
 * Search order:
 * 1. Current working directory
 * 2. Parent directories (up to root)
 * 3. Git repository root (if found)
 * 
 * @param startPath Starting directory for search (defaults to current working directory)
 * @returns Path to .env file if found, null otherwise
 */
export function findDotEnvFile(startPath?: string): string | null {
  const currentPath = startPath ? path.resolve(startPath) : process.cwd();
  let searchPath = currentPath;

  // Search upward until we reach root directory
  while (searchPath !== path.dirname(searchPath)) {
    const envFile = path.join(searchPath, ".env");
    if (fs.existsSync(envFile)) {
      log(`Found .env file at: ${envFile}`);
      return envFile;
    }

    // Check if this is a git repository root
    const gitDir = path.join(searchPath, ".git");
    if (fs.existsSync(gitDir)) {
      log(`Found git repository root at: ${searchPath}`);
    }

    searchPath = path.dirname(searchPath);
  }

  // Check root directory as well
  const rootEnv = path.join(searchPath, ".env");
  if (fs.existsSync(rootEnv)) {
    log(`Found .env file at root: ${rootEnv}`);
    return rootEnv;
  }

  return null;
}

/**
 * Load .env file with improved search strategy.
 * 
 * @param customEnvPath Custom path to .env file (optional)
 */
export function loadDotEnvWithFallback(customEnvPath?: string): void {
  if (customEnvPath) {
    // Use custom path if provided
    if (fs.existsSync(customEnvPath)) {
      try {
        const envConfig = dotenv.parse(fs.readFileSync(customEnvPath));
        for (const k in envConfig) {
          // only load env variables that are not already set in process.env
          if (!process.env.hasOwnProperty(k)) {
            process.env[k] = envConfig[k];
          }
        }
        log(`Loaded custom .env file from: ${customEnvPath}`);
        return;
      } catch (error) {
        log(`Warning: Failed to load custom .env file ${customEnvPath}: ${error}`);
      }
    } else {
      log(`Warning: Custom .env file not found: ${customEnvPath}`);
    }
  }

  // Find .env file using upward search
  const envFile = findDotEnvFile();
  if (envFile) {
    try {
      const envConfig = dotenv.parse(fs.readFileSync(envFile));
      for (const k in envConfig) {
        // only load env variables that are not already set in process.env
        if (!process.env.hasOwnProperty(k)) {
          process.env[k] = envConfig[k];
        }
      }
      log(`Loaded .env file from: ${envFile}`);
    } catch (error) {
      log(`Warning: Failed to load .env file ${envFile}: ${error}`);
    }
  } else {
    log("No .env file found in current directory or parent directories");
  }
}

// Track if .env file has been loaded to avoid duplicate loading
let dotEnvLoaded = false;

/**
 * Load .env file into process.env if it exists
 * This function should be called early to ensure .env variables are available
 * @deprecated Use loadDotEnvWithFallback instead
 */
export function loadDotEnv(): void {
  if (dotEnvLoaded) {
    return; // Already loaded, skip
  }

  loadDotEnvWithFallback();
  dotEnvLoaded = true;
}

/**
 * The SDK uses the following precedence order for configuration (highest to lowest):
 * 1. Explicitly passed configuration in code.
 * 2. Environment variables.
 * 3. .env file.
 * 4. Default configuration.
 */
/**
 * Load configuration with improved .env file search.
 * 
 * @param customConfig Configuration object (if provided, skips env loading)
 * @param customEnvPath Custom path to .env file (optional)
 * @returns Configuration object
 */
export function loadConfig(customConfig?: Config, customEnvPath?: string): Config {
  // If custom config is provided, use it directly
  if (customConfig) {
    return customConfig;
  }

  // Create base config from default values
  const config = defaultConfig();

  // Load .env file with improved search first
  try {
    loadDotEnvWithFallback(customEnvPath);
  } catch (error) {
    log(`Warning: Failed to load .env file: ${error}`);
  }

  // Override with environment variables if they exist (highest priority)
  if (process.env.AGENTBAY_ENDPOINT) {
    config.endpoint = process.env.AGENTBAY_ENDPOINT;
  }

  if (process.env.AGENTBAY_TIMEOUT_MS) {
    const timeout = parseInt(process.env.AGENTBAY_TIMEOUT_MS, 10);
    if (!isNaN(timeout) && timeout > 0) {
      config.timeout_ms = timeout;
    } else {
      log(`Warning: Invalid AGENTBAY_TIMEOUT_MS value: ${process.env.AGENTBAY_TIMEOUT_MS}, using default`);
    }
  }

  return config;
}

export { Config };
