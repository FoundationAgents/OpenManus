/**
 * Browser Context Cookie Persistence Example (TypeScript)
 *
 * This example demonstrates how to use Browser Context to persist cookies
 * across multiple sessions in TypeScript. It shows the complete workflow of:
 * 1. Creating a session with Browser Context
 * 2. Setting cookies in the browser
 * 3. Deleting the session with context synchronization
 * 4. Creating a new session with the same Browser Context
 * 5. Verifying that cookies persist across sessions
 */

import { AgentBay, newCreateSessionParams, BrowserContext, BrowserOptionClass, ContextSync } from 'wuying-agentbay-sdk';
import { chromium } from 'playwright';

async function main(): Promise<void> {
    // Get API key from environment
    const apiKey = process.env.AGENTBAY_API_KEY;
    if (!apiKey) {
        console.error("Error: AGENTBAY_API_KEY environment variable not set");
        return;
    }

    // Initialize AgentBay client
    const agentBay = new AgentBay({ apiKey });
    console.log("AgentBay client initialized");

    // Create a unique context name for this demo
    const contextName = `browser-cookie-demo-${Date.now()}`;

    try {
        // Step 1: Create or get a persistent context for browser data
        console.log(`Step 1: Creating context '${contextName}'...`);
        const contextResult = await agentBay.context.get(contextName, true);

        if (!contextResult.success || !contextResult.context) {
            console.log(`Failed to create context: ${contextResult.errorMessage}`);
            return;
        }

        const context = contextResult.context;
        console.log(`Context created with ID: ${context.id}`);

        // Step 2: Create first session with Browser Context
        console.log("Step 2: Creating first session with Browser Context...");
        const browserContext: BrowserContext = new BrowserContext(context.id,true);

        const params = newCreateSessionParams()
            .withImageId("browser_latest")  // Browser image ID
            .withBrowserContext(browserContext);

        const sessionResult = await agentBay.create(params);
        if (!sessionResult.success || !sessionResult.session) {
            console.log(`Failed to create first session: ${sessionResult.errorMessage}`);
            return;
        }

        const session1 = sessionResult.session;
        console.log(`First session created with ID: ${session1.sessionId}`);

        // Step 3: Initialize browser and set cookies with enhanced error handling
        console.log("Step 3: Initializing browser and setting test cookies...");

        // Initialize browser with retry logic
        console.log("Initializing browser...");
        const browserOptions = new BrowserOptionClass();
        const initSuccess = await session1.browser.initializeAsync(browserOptions);

        if (!initSuccess) {
            console.log("❌ Failed to initialize browser");
            return;
        }

        console.log("✅ Browser initialized successfully");

        // Wait a moment for browser to be fully ready
        await new Promise(resolve => setTimeout(resolve, 2000));

        // Get endpoint URL with validation
        const endpointUrl = await session1.browser.getEndpointUrl();
        console.log(`Raw endpoint URL: ${JSON.stringify(endpointUrl)}`);

        if (!endpointUrl) {
            console.log("❌ Failed to get browser endpoint URL - browser may not be ready");
            return;
        }
        if (!endpointUrl.startsWith('ws://') && !endpointUrl.startsWith('wss://')) {
            console.log(`❌ Invalid endpoint URL format: ${endpointUrl}`);
            console.log("Expected WebSocket URL starting with ws:// or wss://");
            return;
        }

        console.log(`✅ Browser endpoint URL obtained: ${endpointUrl}`);

        // Test data
        const testUrl = "https://www.aliyun.com";
        const testDomain = "aliyun.com";

        // Define test cookies
        const testCookies = [
            {
                name: "demo_cookie_1",
                value: "demo_value_1",
                domain: testDomain,
                path: "/",
                httpOnly: false,
                secure: false,
                expires: Math.floor(Date.now() / 1000) + 3600  // 1 hour from now
            },
            {
                name: "demo_cookie_2",
                value: "demo_value_2",
                domain: testDomain,
                path: "/",
                httpOnly: false,
                secure: false,
                expires: Math.floor(Date.now() / 1000) + 3600  // 1 hour from now
            }
        ];

        // Connect with Playwright with enhanced error handling
        let browser, cdpSession;
        try {
            console.log("Attempting to connect via CDP...");
            browser = await chromium.connectOverCDP(endpointUrl);
            console.log("✅ Successfully connected to browser via CDP");
        } catch (error) {
            console.log(`❌ Failed to connect via CDP: ${error}`);
            console.log("This could be due to:");
            console.log("1. Network connectivity issues");
            console.log("2. Browser process not fully ready");
            console.log("3. Firewall blocking WebSocket connections");
            console.log("4. Invalid endpoint URL format");

            // Try to get more information about the session
            console.log("Session details for debugging:");
            console.log(`Session ID: ${session1.sessionId}`);
            console.log(`Endpoint URL: ${endpointUrl}`);
            return;
        }

        try {
            cdpSession = await browser.newBrowserCDPSession()
            const contextP = browser.contexts()[0] || await browser.newContext();
            const page = await contextP.newPage();

            // Navigate to test URL first (required before setting cookies)
            console.log(`Navigating to ${testUrl}...`);
            await page.goto(testUrl);
            console.log(`✅ Successfully navigated to ${testUrl}`);
            await page.waitForTimeout(2000);

            // Add test cookies
            await contextP.addCookies(testCookies);
            console.log(`✅ Added ${testCookies.length} test cookies`);

            // Verify cookies were set
            const cookies = await contextP.cookies();
            const cookieDict: Record<string, string> = {};
            cookies.forEach((cookie: any) => {
                if (cookie.name) {
                    cookieDict[cookie.name] = cookie.value || '';
                }
            });
            console.log(`Total cookies in first session: ${cookies.length}`);

            // Check our test cookies
            for (const testCookie of testCookies) {
                const cookieName = testCookie.name;
                if (cookieName in cookieDict) {
                    console.log(`✓ Test cookie '${cookieName}' set successfully: ${cookieDict[cookieName]}`);
                } else {
                    console.log(`✗ Test cookie '${cookieName}' not found`);
                }
            }
            await cdpSession.send('Browser.close')
            console.log("First session browser operations completed")

            // Wait for browser to save cookies to file
            console.log("Waiting for browser to save cookies to file...")
            await new Promise(resolve => setTimeout(resolve, 2000));
            console.log("Wait completed")

            await browser.close()
            console.log("First session browser operations completed")

        } finally {
            if (browser) {
                await browser.close();
                console.log("✅ Browser connection closed");
            }
        }

        console.log("First session browser operations completed");

        // Step 4: Delete first session with context synchronization
        console.log("Step 4: Deleting first session with context synchronization...");
        const deleteResult = await agentBay.delete(session1, true);  // syncContext = true

        if (!deleteResult.success) {
            console.log(`Failed to delete first session: ${deleteResult.errorMessage}`);
            return;
        }

        console.log(`First session deleted successfully (RequestID: ${deleteResult.requestId})`);

        // Wait for context sync to complete
        console.log("Waiting for context synchronization to complete...");
        await new Promise(resolve => setTimeout(resolve, 3000));

        // Step 5: Create second session with same Browser Context
        console.log("Step 5: Creating second session with same Browser Context...");
        const sessionResult2 = await agentBay.create(params);

        if (!sessionResult2.success || !sessionResult2.session) {
            console.log(`Failed to create second session: ${sessionResult2.errorMessage}`);
            return;
        }

        const session2 = sessionResult2.session;
        console.log(`Second session created with ID: ${session2.sessionId}`);

        // Step 6: Verify cookie persistence
        console.log("Step 6: Verifying cookie persistence in second session...");

        // Initialize browser in second session
        const initSuccess2 = await session2.browser.initializeAsync(new BrowserOptionClass());
        if (!initSuccess2) {
            console.log("Failed to initialize browser in second session");
            return;
        }

        console.log("Second session browser initialized successfully");

        // Wait for browser to be ready
        await new Promise(resolve => setTimeout(resolve, 2000));

        // Get endpoint URL for second session
        const endpointUrl2 = await session2.browser.getEndpointUrl();
        if (!endpointUrl2) {
            console.log("Failed to get browser endpoint URL for second session");
            return;
        }

        console.log(`Second session browser endpoint URL: ${endpointUrl2}`);

        // Check cookies in second session with error handling
        let browser2;
        try {
            browser2 = await chromium.connectOverCDP(endpointUrl2);

            let context2;
            if (browser2.contexts().length > 0) {
                context2 = await browser2.contexts()[0];
            } else {
                context2 = await browser2.newContext();
            }

            // Read cookies directly from context (without opening any page)
            const cookies2 = await context2.cookies();
            const cookieDict2: Record<string, string> = {};
            cookies2.forEach((cookie: any) => {
                console.log(`Cookie name: ${cookie.name}, value: ${cookie.value}`);
                if (cookie.name) {
                    cookieDict2[cookie.name] = cookie.value || '';
                }
            });

            console.log(`Total cookies in second session: ${cookies2.length}`);

            // Check if our test cookies persisted
            const expectedCookieNames = new Set(["demo_cookie_1", "demo_cookie_2"]);
            const foundCookieNames = new Set(Object.keys(cookieDict2));
            console.log("Found cookie names:", foundCookieNames);
            console.log("Checking cookie persistence...");
            const missingCookies = [...expectedCookieNames].filter(name => !foundCookieNames.has(name));

            if (missingCookies.length > 0) {
                console.log(`✗ Missing test cookies: ${missingCookies.join(', ')}`);
                console.log("Cookie persistence test FAILED");
            } else {
                // Verify cookie values
                let allValuesMatch = true;
                for (const testCookie of testCookies) {
                    const cookieName = testCookie.name;
                    const expectedValue = testCookie.value;
                    const actualValue = cookieDict2[cookieName] || "";

                    if (expectedValue === actualValue) {
                        console.log(`✓ Cookie '${cookieName}' persisted correctly: ${actualValue}`);
                    } else {
                        console.log(`✗ Cookie '${cookieName}' value mismatch. Expected: ${expectedValue}, Actual: ${actualValue}`);
                        allValuesMatch = false;
                    }
                }

                if (allValuesMatch) {
                    console.log("🎉 Cookie persistence test PASSED! All cookies persisted correctly across sessions.");
                } else {
                    console.log("Cookie persistence test FAILED due to value mismatches");
                }
            }

        } catch (error) {
            console.log(`❌ Failed to connect to second session browser: ${error}`);
        } finally {
            if (browser2) {
                await browser2.close();
                console.log("Second session browser operations completed");
            }
        }

        // Step 7: Clean up second session
        console.log("Step 7: Cleaning up second session...");
        const deleteResult2 = await agentBay.delete(session2);

        if (deleteResult2.success) {
            console.log(`Second session deleted successfully (RequestID: ${deleteResult2.requestId})`);
        } else {
            console.log(`Failed to delete second session: ${deleteResult2.errorMessage}`);
        }

    } catch (error) {
        console.log(`❌ Error during demo: ${error}`);
        console.log("\nDebugging information:");
        console.log(`Error type: ${typeof error}`);
        console.log(`Error message: ${error instanceof Error ? error.message : String(error)}`);
        if (error instanceof Error && error.stack) {
            console.log(`Error stack: ${error.stack}`);
        }
    } finally {
        // Clean up context
        try {
            const contextResult = await agentBay.context.get(contextName, false);
            if (contextResult.success && contextResult.context) {
                await agentBay.context.delete(contextResult.context);
                console.log(`Context '${contextName}' deleted`);
            }
        } catch (error) {
            console.log(`Warning: Failed to delete context: ${error}`);
        }
    }

    console.log("\nBrowser Context Cookie Persistence Demo completed!");
}

// Run the example
main().catch(console.error);
