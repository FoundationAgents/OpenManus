/**
 * Example demonstrating wuying-call-for-user message handling with AgentBay SDK.
 *
 * This example shows how to handle the 'wuying-call-for-user' message that can be received
 * during browser automation sessions. The wuying-call-for-user message is triggered when:
 *
 * 1. The browser encounters a situation that requires human intervention
 * 2. Authentication challenges that cannot be automatically resolved
 * 3. Complex verification processes that need user input
 * 4. Security measures that require manual verification
 *
 * When you receive a 'wuying-call-for-user' message, the recommended handling flow is:
 *
 * 1. Parse the console message to identify the message type
 * 2. When 'wuying-call-for-user' is detected, open the session resource URL in a browser
 * 3. Allow the user to interact with the browser to complete the required action
 * 4. Wait for the user to complete the interaction (typically 20-30 seconds)
 * 5. Continue with the automation flow
 *
 * This example demonstrates:
 * - Creating an AgentBay session with browser capabilities
 * - Connecting to the browser via CDP protocol using Playwright
 * - Setting up console message listeners to detect wuying-call-for-user messages
 * - Opening the session resource URL for user interaction
 * - Implementing a wait mechanism for user completion
 * - Taking screenshots for debugging purposes
 */

import { AgentBay, CreateSessionParams } from '../../../src/agent-bay';
import { BrowserOption } from '../../../src/browser';
import { chromium } from 'playwright';
import { exec } from 'child_process';
import * as os from 'os';

async function main(): Promise<void> {
    /**
     * Main function demonstrating wuying-call-for-user message handling.
     * This function sets up a browser session and navigates to JD.com to trigger
     * scenarios that might require user intervention.
     */
    // Get API key from environment variable
    const apiKey = process.env.AGENTBAY_API_KEY;
    if (!apiKey) {
        console.log('Error: AGENTBAY_API_KEY environment variable not set');
        return;
    }

    try {
        // Initialize AgentBay client
        console.log('Initializing AgentBay client...');
        const agentBay = new AgentBay({ apiKey });

        // Create a session
        console.log('Creating a new session...');
        const params: CreateSessionParams = {
            imageId: 'browser_latest', // Specify the image ID
        };
        const sessionResult = await agentBay.create(params);

        if (!sessionResult.success) {
            console.log('Failed to create session');
            return;
        }

        const session = sessionResult.session;
        console.log(`Session created with ID: ${session.sessionId}`);

        const browserOption: BrowserOption = {};
        const initialized = await session.browser.initializeAsync(browserOption);
        if (!initialized) {
            console.log('Failed to initialize browser');
            return;
        }

        console.log('Browser initialized successfully');
        const endpointUrl = await session.browser.getEndpointUrl();
        console.log('endpoint_url =', endpointUrl);
        
        const result = await session.info();
        const info = result.data;
        console.log(`session resource url is ${info.resourceUrl}`);

        // Connect to browser using Playwright
        const browser = await chromium.connectOverCDP(endpointUrl);
        const page = await browser.newPage();
        console.log('🌐 Navigating to jd site...');
        const url = 'https://www.jd.com/';
        await page.goto(url);

        // Listen for console messages
        const handleConsole = async (msg: any) => {
            console.log(`🔍 Received console message: ${msg.text()}`);
            
            // Parse JSON message
            let messageType: string;
            try {
                const messageData = JSON.parse(msg.text());
                messageType = messageData.type || '';
                console.log(`📋 Parsed message type: ${messageType}`);
            } catch (error) {
                // If not JSON, treat as plain text
                messageType = msg.text();
                console.log(`📋 Plain text message: ${messageType}`);
            }

            if (messageType === 'wuying-call-for-user') {
                console.log('📞 Received wuying-call-for-user message');
                console.log(`session resource url is ${info.resourceUrl}`);
                // You can skip this message or use chrome to open url for user handle
                // Following sample code shows how to use chrome open url
                console.log('🌐 Opening browser with session resource URL...');
                
                // Open URL in default browser (cross-platform)
                const platformName = os.platform();
                
                let command: string;
                if (platformName === 'win32') {
                    // Windows: use double quotes to handle special characters
                    command = `start "" "${info.resourceUrl}"`;
                } else if (platformName === 'darwin') {
                    // macOS: use single quotes to handle special characters
                    command = `open '${info.resourceUrl}'`;
                } else {
                    // Linux: use single quotes to handle special characters
                    command = `xdg-open '${info.resourceUrl}'`;
                }
                
                exec(command, (error) => {
                    if (error) {
                        console.log('Failed to open browser:', error);
                    } else {
                        console.log('Browser opened successfully');
                    }
                });
                
                // wait user to interact with the browser
                console.log('⏳ Starting 20 second wait for user interaction...');
                // Use setTimeout to block for 20 seconds for user interaction, also you can check user input
                await new Promise<void>((resolve) => {
                    setTimeout(() => {
                        console.log('⏳ User interaction wait completed');
                        resolve();
                    }, 20000);
                });
            }
        };

        page.on('console', handleConsole);

        await page.waitForTimeout(5000);
        console.log('click login');
        await page.click('.link-login');
        await page.waitForTimeout(25000);
        
        console.log('Test completed');
        
        // Keep browser open for a while to observe results
        await page.waitForTimeout(5000);

        // Take screenshot and print base64, can be pasted directly into Chrome address bar
        try {
            const screenshotBytes = await page.screenshot({ fullPage: false });
            const b64 = screenshotBytes.toString('base64');
            console.log('page_screenshot_base64 = data:image/png;base64,', b64);
        } catch (error) {
            console.log('screenshot failed:', error);
        }
        
        await browser.close();

        // Clean up session
        await agentBay.delete(session);
        console.log('Session cleaned up successfully');

    } catch (error) {
        console.error('Error in main function:', error);
    }
}

// Run the main function if this file is executed directly
if (typeof require !== 'undefined' && require.main === module) {
    main().catch(console.error);
}
