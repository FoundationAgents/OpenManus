package main

import (
	"fmt"
	"os"
	"time"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/ui"
)

func main() {
	// Get API key from environment variable or use a default value for testing
	apiKey := os.Getenv("AGENTBAY_API_KEY")
	if apiKey == "" {
		apiKey = "akm-xxx" // Replace with your actual API key for testing
		fmt.Println("Warning: Using default API key. Set AGENTBAY_API_KEY environment variable for production use.")
	}

	// Initialize the AgentBay client
	agentBay, err := agentbay.NewAgentBay(apiKey)
	if err != nil {
		fmt.Printf("Error initializing AgentBay client: %v\n", err)
		os.Exit(1)
	}

	// Create session parameters with ImageId set to mobile_latest for UI operations
	params := agentbay.NewCreateSessionParams().WithImageId("mobile_latest")

	// Create a new session
	fmt.Println("\nCreating a new session with mobile_latest image...")
	sessionResult, err := agentBay.Create(params)
	if err != nil {
		fmt.Printf("\nError creating session: %v\n", err)
		os.Exit(1)
	}
	session := sessionResult.Session
	fmt.Printf("\nSession created with ID: %s (RequestID: %s)\n", session.SessionID, sessionResult.RequestID)
	defer func() {
		// Clean up by deleting the session when we're done
		fmt.Println("\nDeleting the session...")
		deleteResult, err := session.Delete()
		if err != nil {
			fmt.Printf("Error deleting session: %v\n", err)
		} else {
			fmt.Printf("Session deleted successfully (RequestID: %s)\n", deleteResult.RequestID)
		}
	}()

	// 1. Take a screenshot
	fmt.Println("\n1. Taking a screenshot...")
	screenshotResult, err := session.UI.Screenshot()
	if err != nil {
		fmt.Printf("Error taking screenshot: %v\n", err)
	} else {
		// The screenshot operation was successful
		fmt.Printf("Screenshot taken successfully (RequestID: %s, Success: %v, ComponentID: %s)\n",
			screenshotResult.RequestID, screenshotResult.Success, screenshotResult.ComponentID)

		// Note: The current implementation returns success status but not the actual image data
		// The screenshot data would need to be retrieved separately if available
	}

	// 2. Get all UI elements
	fmt.Println("\n2. Getting all UI elements...")
	elementsResult, err := session.UI.GetAllUIElements(2000) // 2 second timeout
	if err != nil {
		fmt.Printf("Error getting UI elements: %v\n", err)
	} else if len(elementsResult.Elements) == 0 {
		fmt.Println("No UI elements found.")
	} else {
		fmt.Printf("Found %d UI elements (RequestID: %s)\n", len(elementsResult.Elements), elementsResult.RequestID)
		// Print details of the first few elements if available
		elementsToShow := 3
		if len(elementsResult.Elements) < elementsToShow {
			elementsToShow = len(elementsResult.Elements)
		}

		fmt.Println("\nSample of UI elements found:")
		for i := 0; i < elementsToShow; i++ {
			elem := elementsResult.Elements[i]
			fmt.Printf("Element #%d:\n", i+1)
			fmt.Printf("  Type: %v\n", elem.Type)
			fmt.Printf("  Text: %v\n", elem.Text)
			fmt.Printf("  Bounds: %v\n", elem.Bounds)
			fmt.Printf("  ResourceId: %v\n", elem.ResourceID)
			fmt.Println()
		}
	}

	// 3. Get clickable UI elements
	fmt.Println("\n3. Getting clickable UI elements...")
	clickableElementsResult, err := session.UI.GetClickableUIElements(2000) // 2 second timeout
	if err != nil {
		fmt.Printf("Error getting clickable UI elements: %v\n", err)
	} else if len(clickableElementsResult.Elements) == 0 {
		fmt.Println("No clickable UI elements found.")
	} else {
		fmt.Printf("Found %d clickable UI elements (RequestID: %s)\n", len(clickableElementsResult.Elements), clickableElementsResult.RequestID)
		// Print details of the first few clickable elements if available
		elementsToShow := 3
		if len(clickableElementsResult.Elements) < elementsToShow {
			elementsToShow = len(clickableElementsResult.Elements)
		}

		fmt.Println("\nSample of clickable UI elements found:")
		for i := 0; i < elementsToShow; i++ {
			elem := clickableElementsResult.Elements[i]
			fmt.Printf("Element #%d:\n", i+1)
			fmt.Printf("  Type: %v\n", elem.Type)
			fmt.Printf("  Text: %v\n", elem.Text)
			fmt.Printf("  Bounds: %v\n", elem.Bounds)
			fmt.Printf("  ResourceId: %v\n", elem.ResourceID)
			fmt.Println()
		}
	}

	// 4. Send key event (HOME key)
	fmt.Println("\n4. Sending HOME key event...")
	keyResult, err := session.UI.SendKey(int(ui.KEYCODE_HOME)) // Use KeyCode.HOME constant
	if err != nil {
		fmt.Printf("Error sending HOME key: %v\n", err)
	} else {
		fmt.Printf("HOME key sent successfully (RequestID: %s)\n", keyResult.RequestID)
	}

	// Sleep briefly to allow UI to update after HOME key
	time.Sleep(1 * time.Second)

	// 5. Input text
	fmt.Println("\n5. Inputting text...")
	inputResult, err := session.UI.InputText("Hello from AgentBay SDK!")
	if err != nil {
		fmt.Printf("Error inputting text: %v\n", err)
	} else {
		fmt.Printf("Text input successful (RequestID: %s)\n", inputResult.RequestID)
	}

	// 6. Click a position on screen
	fmt.Println("\n6. Clicking on screen position...")
	// Coordinates for center of screen (example values)
	x := 540
	y := 960
	clickResult, err := session.UI.Click(x, y, "left")
	if err != nil {
		fmt.Printf("Error clicking on position (%d,%d): %v\n", x, y, err)
	} else {
		fmt.Printf("Successfully clicked at position (%d,%d) (RequestID: %s)\n", x, y, clickResult.RequestID)
	}

	// Sleep briefly to allow UI to update after click
	time.Sleep(1 * time.Second)

	// 7. Swipe on screen
	fmt.Println("\n7. Performing swipe gesture...")
	startX := 540
	startY := 1500
	endX := 540
	endY := 500
	swipeDuration := 10000 // milliseconds
	swipeResult, err := session.UI.Swipe(startX, startY, endX, endY, swipeDuration)
	if err != nil {
		fmt.Printf("Error performing swipe from (%d,%d) to (%d,%d): %v\n",
			startX, startY, endX, endY, err)
	} else {
		fmt.Printf("Successfully swiped from (%d,%d) to (%d,%d) (RequestID: %s)\n",
			startX, startY, endX, endY, swipeResult.RequestID)
	}

	// 8. Take another screenshot after interactions
	fmt.Println("\n8. Taking another screenshot after interactions...")
	screenshot2Result, err := session.UI.Screenshot()
	if err != nil {
		fmt.Printf("Error taking second screenshot: %v\n", err)
	} else {
		fmt.Printf("Second screenshot taken successfully (RequestID: %s, Success: %v, ComponentID: %s)\n",
			screenshot2Result.RequestID, screenshot2Result.Success, screenshot2Result.ComponentID)

		// Note: The current implementation returns success status but not the actual image data
		// The screenshot data would need to be retrieved separately if available
	}

	fmt.Println("\nUI examples completed successfully!")
}
