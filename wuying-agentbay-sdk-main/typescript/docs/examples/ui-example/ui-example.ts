import { AgentBay, log, logError } from 'wuying-agentbay-sdk';
import * as fs from 'fs';

// Helper function to parse bounds from a bounds string like "[0,100][200,300]"
// Returns x1, y1, x2, y2
function parseBounds(boundsStr: string): { x1: number, y1: number, x2: number, y2: number } | null {
  if (!boundsStr || boundsStr.length < 9) {
    return null;
  }

  try {
    // Remove brackets and split by "]["
    const cleaned = boundsStr.substring(1, boundsStr.length - 1);
    const parts = cleaned.split('][');
    if (parts.length !== 2) {
      return null;
    }

    // Parse the coordinates
    const topLeft = parts[0].split(',');
    const bottomRight = parts[1].split(',');

    if (topLeft.length !== 2 || bottomRight.length !== 2) {
      return null;
    }

    return {
      x1: parseInt(topLeft[0], 10),
      y1: parseInt(topLeft[1], 10),
      x2: parseInt(bottomRight[0], 10),
      y2: parseInt(bottomRight[1], 10)
    };
  } catch (error) {
    return null;
  }
}

async function main() {
  // Get API key from environment variable or use default value for testing
   const apiKey = process.env.AGENTBAY_API_KEY || 'akm-xxx'; // Replace with your actual API key
  if (!process.env.AGENTBAY_API_KEY) {
    log('Warning: Using placeholder API key. Set AGENTBAY_API_KEY environment variable for production use.');
  }

  // Initialize the AgentBay client
  const agentBay = new AgentBay({ apiKey });

  // Create session parameters with imageId set to mobile_latest for UI operations
  const params = {
    imageId: 'mobile_latest'
  };

  // Create a new session
  log('\nCreating a new session with mobile_latest image...');
  const createResponse = await agentBay.create(params);
  const session = createResponse.session;
  log(`\nSession created with ID: ${session.sessionId}`);
  log(`Create Session RequestId: ${createResponse.requestId}`);

  try {
    // 1. Take a screenshot using the correct tool name
    log('\n1. Taking a screenshot...');
    try {
      const screenshotResponse = await session.ui.screenshot();
      // The screenshot is returned as a base64-encoded string
      log(`Screenshot taken successfully. Base64 data length: ${screenshotResponse.data.length} bytes`);
      log(`Screenshot RequestId: ${screenshotResponse.requestId}`);

      // Optional: Save the screenshot to a file
      // Uncomment the following lines to save the screenshot
      const imgData = Buffer.from(screenshotResponse.data, 'base64');
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
      const filename = `screenshot_${timestamp}.png`;
      fs.writeFileSync(filename, imgData);
      log(`Screenshot saved to ${filename}`);
    } catch (error) {
      log(`Error taking screenshot: ${error}`);
    }

    // 2. Get all UI elements
    log('\n2. Getting all UI elements...');
    try {
      const elementsResponse = await session.ui.getAllUIElements(2000); // 2 second timeout

      log(`Found ${elementsResponse.elements.length} UI elements`);
      log(`Get All UI Elements RequestId: ${elementsResponse.requestId}`);
      // Print details of the first few elements if available
      const elementsToShow = Math.min(elementsResponse.elements.length, 3);

      log('\nSample of UI elements found:');
      for (let i = 0; i < elementsToShow; i++) {
        const elem = elementsResponse.elements[i];
        log(`Element #${i+1}:`);
        log(`  Type: ${elem.type}`);
        log(`  Text: ${elem.text}`);
        log(`  Bounds: ${elem.bounds}`);
        log(`  ResourceId: ${elem.resourceId}`);
      }
    } catch (error) {
      log(`Error getting UI elements: ${error}`);
    }

    // 3. Get clickable UI elements
    log('\n3. Getting clickable UI elements...');
    try {
      const clickableResponse = await session.ui.getClickableUIElements(2000); // 2 second timeout

      log(`Found ${clickableResponse.elements.length} clickable UI elements`);
      log(`Get Clickable UI Elements RequestId: ${clickableResponse.requestId}`);
      // Print details of the first few clickable elements if available
      const elementsToShow = Math.min(clickableResponse.elements.length, 3);

      log('\nSample of clickable UI elements found:');
      for (let i = 0; i < elementsToShow; i++) {
        const elem = clickableResponse.elements[i];
        log(`Element #${i+1}:`);
        log(`  Type: ${elem.type}`);
        log(`  Text: ${elem.text}`);
        log(`  Bounds: ${elem.bounds}`);
        log(`  ResourceId: ${elem.resourceId}`);
      }
    } catch (error) {
      log(`Error getting clickable UI elements: ${error}`);
    }

    // 4. Send key event (HOME key)
    log('\n4. Sending HOME key event...');
    try {
      const sendKeyResponse = await session.ui.sendKey(3); // 3 is HOME key code
      log('HOME key sent successfully');
      log(`Send Key RequestId: ${sendKeyResponse.requestId}`);
    } catch (error) {
      log(`Error sending HOME key: ${error}`);
    }

    // Sleep briefly to allow UI to update after HOME key
    await new Promise(resolve => setTimeout(resolve, 1000)); // 1 second

    // 5. Input text
    log('\n5. Inputting text...');
    try {
      const inputResponse = await session.ui.inputText("Hello from AgentBay SDK!");
      log('Text input successful');
      log(`Input Text RequestId: ${inputResponse.requestId}`);
    } catch (error) {
      log(`Error inputting text: ${error}`);
    }

    // 6. Click a position on screen
    log('\n6. Clicking on screen position...');
    // Coordinates for center of screen (example values)
    const x = 540;
    const y = 960;
    try {
      const clickResponse = await session.ui.click(x, y, "left");
      log(`Successfully clicked at position (${x},${y})`);
      log(`Click RequestId: ${clickResponse.requestId}`);
    } catch (error) {
      log(`Error clicking on position (${x},${y}): ${error}`);
    }

    // Sleep briefly to allow UI to update after click
    await new Promise(resolve => setTimeout(resolve, 1000)); // 1 second

    // 7. Swipe on screen
    log('\n7. Performing swipe gesture...');
    const startX = 540;
    const startY = 1500;
    const endX = 540;
    const endY = 500;
    const swipeDuration = 500; // milliseconds
    try {
      const swipeResponse = await session.ui.swipe(startX, startY, endX, endY, swipeDuration);
      log(`Successfully swiped from (${startX},${startY}) to (${endX},${endY})`);
      log(`Swipe RequestId: ${swipeResponse.requestId}`);
    } catch (error) {
      log(`Error performing swipe from (${startX},${startY}) to (${endX},${endY}): ${error}`);
    }

    // 8. Take another screenshot after interactions
    log('\n8. Taking another screenshot after interactions...');
    try {
      const screenshot2Response = await session.ui.screenshot();
      log(`Second screenshot taken successfully. Base64 data length: ${screenshot2Response.data.length} bytes`);
      log(`Second Screenshot RequestId: ${screenshot2Response.requestId}`);

      const imgData = Buffer.from(screenshot2Response.data, 'base64');
      // Save the second screenshot
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
      const filename = `screenshot_after_${timestamp}.png`;
      fs.writeFileSync(filename, imgData);
      log(`Screenshot saved to ${filename}`);
    } catch (error) {
      log(`Error taking second screenshot: ${error}`);
    }

    log('\nUI examples completed successfully!');

  } finally {
    // Clean up by deleting the session when we're done
    log('\nDeleting the session...');
    try {
      const deleteResponse = await agentBay.delete(session);
      log('Session deleted successfully');
      log(`Delete Session RequestId: ${deleteResponse.requestId}`);
    } catch (error) {
      log(`Error deleting session: ${error}`);
    }
  }
}

main().catch(error => {
  logError('Error in main execution:', error);
  process.exit(1);
});
