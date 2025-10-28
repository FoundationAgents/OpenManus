/**
 * Example demonstrating Browser Proxy configuration with AgentBay SDK.
 *
 * This example shows how to use proxy functionality with AgentBay SDK. 
 * AgentBay supports two types of proxies:
 *
 * 1. Custom Proxy:
 *    - Uses user-provided proxy servers
 *    - Supports HTTP/HTTPS/SOCKS proxies
 *    - Optionally provides username and password for authentication
 *
 * 2. Wuying Proxy:
 *    - Uses Alibaba Cloud Wuying proxy service
 *    - Supports two strategies:
 *      * restricted: Uses fixed proxy nodes
 *      * polling: Rotates through proxy pool nodes
 *
 * This example demonstrates:
 * - Create AIBrowser session with proxy configuration
 * - Use playwright to connect to AIBrowser instance through CDP protocol
 * - Verify the proxy's public IP address
 */

// @ts-nocheck
import { AgentBay, CreateSessionParams } from '../../../src/agent-bay';
import { BrowserOption, BrowserProxy } from '../../../src/browser';
import { chromium } from 'playwright';

interface IpResponse {
    origin: string;
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

        // ==================== Proxy Configuration Examples ====================
        
        // Example 1: Custom Proxy Configuration
        // Suitable for users who have their own proxy servers
        // const browserProxy: BrowserProxy = {
        //     type: 'custom',
        //     server: 'http://127.0.0.1:9090',
        //     username: 'username',
        //     password: 'password',
        //     toMap: function() {
        //         return {
        //             type: this.type,
        //             server: this.server,
        //             username: this.username,
        //             password: this.password
        //         };
        //     }
        // };

        // Example 2: Wuying Proxy - Polling Strategy
        // Rotates through proxy pool nodes, suitable for scenarios requiring frequent IP switching
        const browserProxy: BrowserProxy = {
            type: 'wuying',
            strategy: 'polling',
            pollsize: 2,
            toMap: function() {
                return {
                    type: this.type,
                    strategy: this.strategy,
                    pollsize: this.pollsize
                };
            }
        };

        // Example 3: Wuying Proxy - Restricted Strategy
        // Uses fixed proxy nodes, suitable for scenarios requiring stable IP
        // const browserProxy: BrowserProxy = {
        //     type: 'wuying',
        //     strategy: 'restricted',
        //     toMap: function() {
        //         return {
        //             type: this.type,
        //             strategy: this.strategy
        //         };
        //     }
        // };

        // Create browser option with proxy configuration, now only support one proxy
        const browserOption: BrowserOption = {
            proxies: [browserProxy]
        };

        const initialized = await session.browser.initializeAsync(browserOption);
        if (initialized) {
            const endpointUrl = await session.browser.getEndpointUrl();
            console.log('endpoint_url =', endpointUrl);

            const browser = await chromium.connectOverCDP(endpointUrl);
            const context = browser.contexts()[0];
            const page = await context.newPage();

            try {
                // ==================== Verify Proxy IP ====================
                console.log('\n--- Check proxy public IP start ---');
                await page.goto('https://httpbin.org/ip');

                const response = await page.evaluate((): IpResponse => {
                    return JSON.parse(document.body.textContent || '{}');
                });
                const publicIp = response.origin || '';
                console.log('proxy public IP:', publicIp);
                console.log('--- Check proxy public IP end ---');

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
