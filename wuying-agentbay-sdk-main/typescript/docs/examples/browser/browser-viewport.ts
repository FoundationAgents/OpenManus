/**
 * Example demonstrating Browser Viewport configuration with AgentBay SDK.
 *
 * This example shows how to initialize the browser with custom viewport and user-agent settings:
 * - Create AIBrowser session with custom viewport and user-agent.
 * - Use playwright to connect to AIBrowser instance through CDP protocol
 * - Verify custom viewport and screen size
 * - Verify custom user agent
 */

// @ts-nocheck
import { AgentBay, CreateSessionParams } from '../../../src/agent-bay';
import { BrowserOption, BrowserViewport } from '../../../src/browser';
import { chromium } from 'playwright';

interface ScreenInfo {
    outerWidth: number;
    outerHeight: number;
    innerWidth: number;
    innerHeight: number;
    width: number;
    height: number;
    availWidth: number;
    availHeight: number;
    colorDepth: number;
    pixelDepth: number;
}

interface WindowInfo {
    screen: ScreenInfo | null;
}

interface UserAgentResponse {
    'user-agent': string;
}

async function main(): Promise<void> {
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
            imageId: 'browser_latest',
        };
        const sessionResult = await agentBay.create(params);

        if (!sessionResult.success) {
            console.log('Failed to create session');
            return;
        }

        const session = sessionResult.session;
        console.log(`Session created with ID: ${session.sessionId}`);

        // Create browser option with viewport and user-agent
        const browserOption: BrowserOption = {
            userAgent: 'Mozilla/5.0 (Mocked Windows Desktop)',
            viewport: { width: 1920, height: 1080 },
            // screen: { width: 1920, height: 1080 },
        };

        const initialized = await session.browser.initializeAsync(browserOption);
        if (initialized) {
            const endpointUrl = await session.browser.getEndpointUrl();
            console.log('endpoint_url =', endpointUrl);

            const browser = await chromium.connectOverCDP(endpointUrl);
            const context = browser.contexts()[0];
            const page = await context.newPage();

            try {
                // Check custom viewport and screen size
                console.log('\n--- Check window Properties ---');
                const windowInfo = await page.evaluate((): WindowInfo => {
                    const screenInfo = window.screen ? {
                        outerWidth: window.outerWidth,
                        outerHeight: window.outerHeight,
                        innerWidth: window.innerWidth,
                        innerHeight: window.innerHeight,
                        width: window.screen.width,
                        height: window.screen.height,
                        availWidth: window.screen.availWidth,
                        availHeight: window.screen.availHeight,
                        colorDepth: window.screen.colorDepth,
                        pixelDepth: window.screen.pixelDepth
                    } : null;
                    
                    return {
                        screen: screenInfo
                    };
                });
                console.log('Screen Info:', windowInfo.screen);
                
                // Check custom user agent
                console.log('\n--- Check User Agent ---');
                await page.goto('https://httpbin.org/user-agent');

                const response = await page.evaluate((): UserAgentResponse => {
                    return JSON.parse(document.body.textContent || '{}');
                });
                const userAgent = response['user-agent'] || '';
                console.log('User Agent:', userAgent);

                await page.waitForTimeout(3000);
            } finally {
                await browser.close();
            }
        }

        // Clean up session
        await agentBay.delete(session);
    } catch (error) {
        console.error('Error:', error);
    }
}

if (require.main === module) {
    main().catch(console.error);
}
