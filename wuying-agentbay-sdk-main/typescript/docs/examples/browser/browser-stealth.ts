/**
 * Example demonstrating Browser Stealth mode with AgentBay SDK.
 *
 * This example shows how to use stealth mode with fingerprint to avoid detection
 * by anti-bot services. It will generate a random, realistic browser fingerprint
 * and make the browser behave more like a real user:
 * - Create AIBrowser session with stealth mode and simulate a Windows desktop browser.
 * - Use playwright to connect to AIBrowser instance through CDP protocol
 * - Verify user agent and navigator properties
 */

// @ts-nocheck
import { AgentBay, CreateSessionParams } from '../../../src/agent-bay';
import { BrowserOption, BrowserFingerprint } from '../../../src/browser';
import { chromium } from 'playwright';

async function main(): Promise<void> {
  // Get API key from environment variable
  const apiKey = process.env.AGENTBAY_API_KEY;
  if (!apiKey) {
    console.log("Error: AGENTBAY_API_KEY environment variable not set");
    return;
  }

  try {
    // Initialize AgentBay client
    console.log("Initializing AgentBay client...");
    const agentBay = new AgentBay({ apiKey });

    // Create a session
    console.log("Creating a new session...");
    const params: CreateSessionParams = {
      imageId: "browser_latest",
    };
    const sessionResult = await agentBay.create(params);

    if (!sessionResult.success) {
      console.log("Failed to create session");
      return;
    }

    const session = sessionResult.session;
    console.log(`Session created with ID: ${session.sessionId}`);

    /**
     * Create browser fingerprint option
     * - devices: desktop or mobile
     * - operatingSystems: windows, macos, linux, android, ios
     *
     * You can specify one or multiple values for each parameter.
     * But if you specify devices as desktop and operatingSystems as android/ios,
     * the fingerprint feature will not work.
     */
    const browserFingerprint: BrowserFingerprint = {
      devices: ["desktop"],
      operatingSystems: ["windows"],
      locales: ["zh-CN", "zh"]
    };

    // Create browser option with stealth mode and fingerprint option limit.
    // Stealth mode helps to avoid detection by anti-bot services. It will
    // generate a random, realistic browser fingerprint and make the browser
    // behave more like a real user.
    const browserOption: BrowserOption = {
      useStealth: true,
      fingerprint: browserFingerprint
    };

    const initialized = await session.browser.initializeAsync(browserOption);
    if (!initialized) {
      console.log("Failed to initialize browser");
      return;
    }

    const endpointUrl = await session.browser.getEndpointUrl();
    console.log("endpoint_url =", endpointUrl);

    // Connect to browser using Playwright
    const browser = await chromium.connectOverCDP(endpointUrl);
    const context = browser.contexts()[0];
    const page = await context.newPage();

    // Check user agent
    console.log("\n--- Check User Agent ---");
    await page.goto("https://httpbin.org/user-agent");

    const response = await page.evaluate(() => JSON.parse(document.body.textContent));
    const userAgent = response["user-agent"] || "";
    console.log(`User Agent: ${userAgent}`);

    // Check navigator properties
    console.log("\n--- Check Navigator Properties ---");
    const navInfo = await page.evaluate(() => ({
      platform: navigator.platform,
      language: navigator.language,
      languages: navigator.languages,
      webdriver: navigator.webdriver
    }));

    console.log(`Platform: ${navInfo.platform}`);
    console.log(`Language: ${navInfo.language}`);
    console.log(`Languages: ${navInfo.languages}`);
    console.log(`WebDriver: ${navInfo.webdriver}`);

    await page.waitForTimeout(3000);
    await browser.close();

    // Clean up session
    await agentBay.delete(session);
    console.log("Session cleaned up successfully");

  } catch (error) {
    console.error("Error in main function:", error);
  }
}

if (require.main === module) {
  main().catch(console.error);
}
