package main

import (
	"fmt"
	"os"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/models"
)

// This example demonstrates how to create, list, and delete sessions
// using the Wuying AgentBay SDK.

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

	// Create a new session with default parameters
	fmt.Println("\n1. Creating a new session with default parameters...")
	sessionResult, err := agentBay.Create(nil)
	if err != nil {
		fmt.Printf("\nError creating session: %v\n", err)
		os.Exit(1)
	}
	session := sessionResult.Session
	fmt.Printf("Session created with ID: %s (RequestID: %s)\n", session.SessionID, sessionResult.RequestID)

	// Create a mobile session with whitelist configuration
	fmt.Println("\n2. Creating mobile session with whitelist configuration...")
	// Create mobile configuration with whitelist
	appRule := &models.AppManagerRule{
		RuleType: "White",
		AppPackageNameList: []string{
			"com.android.settings",
			"com.example.test.app",
			"com.trusted.service",
		},
	}
	mobileConfig := &models.MobileExtraConfig{
		LockResolution: true,
		AppManagerRule: appRule,
	}
	extraConfigs := &models.ExtraConfigs{
		Mobile: mobileConfig,
	}

	mobileWhitelistParams := agentbay.NewCreateSessionParams().
		WithImageId("mobile_latest").
		WithLabels(map[string]string{
			"project":     "mobile-testing",
			"config_type": "whitelist",
			"environment": "development",
		}).
		WithExtraConfigs(extraConfigs)

	mobileWhitelistResult, err := agentBay.Create(mobileWhitelistParams)
	if err != nil {
		fmt.Printf("Error creating mobile whitelist session: %v\n", err)
	} else {
		mobileWhitelistSession := mobileWhitelistResult.Session
		fmt.Printf("Mobile whitelist session created with ID: %s (RequestID: %s)\n",
			mobileWhitelistSession.SessionID, mobileWhitelistResult.RequestID)

		// Clean up mobile whitelist session
		defer func() {
			if deleteResult, err := mobileWhitelistSession.Delete(); err != nil {
				fmt.Printf("Error deleting mobile whitelist session: %v\n", err)
			} else {
				fmt.Printf("Mobile whitelist session deleted (RequestID: %s)\n", deleteResult.RequestID)
			}
		}()
	}

	// Create a mobile session with blacklist configuration
	fmt.Println("\n3. Creating mobile session with blacklist configuration...")
	// Create mobile configuration with blacklist
	blacklistAppRule := &models.AppManagerRule{
		RuleType: "Black",
		AppPackageNameList: []string{
			"com.malware.suspicious",
			"com.unwanted.adware",
			"com.blocked.app",
		},
	}
	blacklistMobileConfig := &models.MobileExtraConfig{
		LockResolution: false,
		AppManagerRule: blacklistAppRule,
	}
	blacklistExtraConfigs := &models.ExtraConfigs{
		Mobile: blacklistMobileConfig,
	}

	mobileBlacklistParams := agentbay.NewCreateSessionParams().
		WithImageId("mobile_latest").
		WithLabels(map[string]string{
			"project":     "mobile-security",
			"config_type": "blacklist",
			"environment": "production",
			"security":    "enabled",
		}).
		WithExtraConfigs(blacklistExtraConfigs)

	mobileBlacklistResult, err := agentBay.Create(mobileBlacklistParams)
	if err != nil {
		fmt.Printf("Error creating mobile blacklist session: %v\n", err)
	} else {
		mobileBlacklistSession := mobileBlacklistResult.Session
		fmt.Printf("Mobile blacklist session created with ID: %s (RequestID: %s)\n",
			mobileBlacklistSession.SessionID, mobileBlacklistResult.RequestID)

		// Clean up mobile blacklist session
		defer func() {
			if deleteResult, err := mobileBlacklistSession.Delete(); err != nil {
				fmt.Printf("Error deleting mobile blacklist session: %v\n", err)
			} else {
				fmt.Printf("Mobile blacklist session deleted (RequestID: %s)\n", deleteResult.RequestID)
			}
		}()
	}


	// Create multiple sessions to demonstrate listing
	fmt.Println("\nCreating additional sessions...")
	var additionalSessions []*agentbay.Session
	for i := 0; i < 2; i++ {
		additionalSessionResult, err := agentBay.Create(nil)
		if err != nil {
			fmt.Printf("\nError creating additional session: %v\n", err)
			continue
		}
		additionalSession := additionalSessionResult.Session
		fmt.Printf("Additional session created with ID: %s (RequestID: %s)\n", additionalSession.SessionID, additionalSessionResult.RequestID)

		// Store the session for later cleanup
		additionalSessions = append(additionalSessions, additionalSession)
	}


	// Clean up all sessions
	fmt.Println("\nCleaning up sessions...")
	// First delete the initial session
	deleteResult, err := session.Delete()
	if err != nil {
		fmt.Printf("Error deleting session %s: %v\n", session.SessionID, err)
	} else {
		fmt.Printf("Session %s deleted successfully (RequestID: %s)\n", session.SessionID, deleteResult.RequestID)
	}

	// Then delete the additional sessions
	for _, s := range additionalSessions {
		deleteResult, err := s.Delete()
		if err != nil {
			fmt.Printf("Error deleting session %s: %v\n", s.SessionID, err)
		} else {
			fmt.Printf("Session %s deleted successfully (RequestID: %s)\n", s.SessionID, deleteResult.RequestID)
		}
	}

	fmt.Println("All sessions cleanup completed.")
}
