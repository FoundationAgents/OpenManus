/**
 * Example demonstrating AIBrowser capabilities with AgentBay SDK.
 * This example shows how to use AIBrowser to solve captcha automatically, including:
 * - Create AIBrowser session
 * - Use playwright to connect to AIBrowser instance through CDP protocol
 * - Set solve_captchas to be True and goto tongcheng website
 * - We will encounter a captcha and we will solve it automatically.
 */

import { AgentBay, CreateSessionParams } from '../../../src/agent-bay';
import { BrowserOption } from '../../../src/browser';
import { chromium } from 'playwright';

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
            imageId: 'browser_latest', // Specify the image ID
        };
        const sessionResult = await agentBay.create(params);

        if (!sessionResult.success) {
            console.log('Failed to create session');
            return;
        }

        const session = sessionResult.session;
        console.log(`Session created with ID: ${session.sessionId}`);

        const browserOption: BrowserOption = {
            useStealth: true,
            solveCaptchas: true,
        };

        const initialized = await session.browser.initializeAsync(browserOption);
        if (!initialized) {
            console.log('Failed to initialize browser');
            return;
        }

        console.log('Browser initialized successfully');
        const endpointUrl = await session.browser.getEndpointUrl();
        console.log('endpoint_url =', endpointUrl);

        // Connect to browser using Playwright
        const browser = await chromium.connectOverCDP(endpointUrl);
        const page = await browser.newPage();
        console.log('🌐 Navigating to tongcheng site...');
        const url = 'https://passport.ly.com/Passport/GetPassword';
        await page.goto(url, { waitUntil: 'domcontentloaded' });

        // Use selector to locate input field
        const inputElement = await page.waitForSelector('#name_in', { timeout: 10000 });
        console.log('Found login name input field: #name_in');
        
        // Clear input field and enter phone number
        const phoneNumber = '15011556760';
        console.log(`Entering phone number: ${phoneNumber}`);
        
        await inputElement.click();
        await inputElement.fill(''); // Clear input field
        await inputElement.type(phoneNumber);
        console.log('Waiting for captcha');

        // Wait a moment to ensure input is complete
        await page.waitForTimeout(1000);
        
        console.log('Clicking next step button...');
        await page.click('#next_step1');

        // Listen for captcha processing messages
        let captchaSolvingStarted = false;
        let captchaSolvingFinished = false;

        // Listen for console messages
        const handleConsole = (msg: any) => {
            console.log(`🔍 Received console message: ${msg.text()}`);
            if (msg.text() === 'wuying-captcha-solving-started') {
                captchaSolvingStarted = true;
                console.log('🎯 Setting captchaSolvingStarted = true');
                page.evaluate('window.captchaSolvingStarted = true; window.captchaSolvingFinished = false;');
            } else if (msg.text() === 'wuying-captcha-solving-finished') {
                captchaSolvingFinished = true;
                console.log('✅ Setting captchaSolvingFinished = true');
                page.evaluate('window.captchaSolvingFinished = true;');
            }
        };

        page.on('console', handleConsole);

        // Wait 1 second first, then check if captcha processing has started
        try {
            await page.waitForTimeout(1000);
            await page.waitForFunction('() => window.captchaSolvingStarted === true', { timeout: 1000 });
            console.log('🎯 Detected captcha processing started, waiting for completion...');
            
            // If start is detected, wait for completion (max 30 seconds)
            try {
                await page.waitForFunction('() => window.captchaSolvingFinished === true', { timeout: 30000 });
                console.log('✅ Captcha processing completed');
            } catch (error) {
                console.log('⚠️ Captcha processing timeout, may still be in progress');
            }
                
        } catch (error) {
            console.log('⏭️ No captcha processing detected, continuing execution');
        }
        
        await page.waitForTimeout(2000);
        await page.type('#step2_yzm', '1234');
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

if (require.main === module) {
    main().catch(console.error);
}
