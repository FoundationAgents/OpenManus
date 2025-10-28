import "dotenv/config";
import { log } from "../../src/utils/logger";

// Define Node.js process if it's not available
declare namespace NodeJS {
  interface ProcessEnv {
    [key: string]: string | undefined;
  }
}

declare var process: {
  env: {
    [key: string]: string | undefined;
  };
};

/**
 * Get API key for testing
 * @returns The API key to use for tests
 */
export function getTestApiKey(): string {
  // For Node.js environments
  let apiKey: string | undefined;
  try {
    apiKey = process.env.AGENTBAY_API_KEY;
  } catch (e) {
    // process is not defined in some environments
  }

  if (!apiKey) {
    log(
      "Warning: Using default API key. Set AGENTBAY_API_KEY environment variable for testing."
    );
    return "akm-xxx"; // Replace with your test API key
  }
  return apiKey;
}

/**
 * Check if a string contains "tool not found"
 * @param s The string to check
 * @returns True if the string contains "tool not found"
 */
export function containsToolNotFound(s: string): boolean {
  return s.toLowerCase().includes("tool not found");
}

/**
 * Extract resourceId from a URL
 * @param url The URL to extract from
 * @returns The extracted resourceId or empty string if not found
 */
export function extractResourceId(url: string): string {
  const matches = url.match(/resourceId=([^&]+)/);
  if (matches && matches.length > 1) {
    return matches[1];
  }
  return "";
}

/**
 * Wait for a specified amount of time
 * @param ms Milliseconds to wait
 * @returns A promise that resolves after the specified time
 */
export function wait(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Generate a random string for test data
 * @param length Length of the string to generate
 * @returns A random string
 */
export function randomString(length: number = 8): string {
  const chars =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
  let result = "";
  for (let i = 0; i < length; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return result;
}

/**
 *
 * @returns A unique ID for testing
 */
export function generateUniqueId(): string {
  const timestamp = Date.now() * 1000;
  const randomPart = Math.floor(Math.random() * 10001);

  return `${timestamp}-${randomPart}`;
}
