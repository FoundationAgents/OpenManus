package integration

import (
	"fmt"
	"os"
	"strings"
	"testing"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/models"
)

// TestSessionExtraConfigsIntegration contains integration test cases for session creation
// with extra configurations using real API.
func TestSessionExtraConfigsIntegration_MobileConfig(t *testing.T) {
	// Get API Key
	apiKey := os.Getenv("AGENTBAY_API_KEY")
	if apiKey == "" {
		t.Fatal("AGENTBAY_API_KEY environment variable is not set")
	}

	fmt.Println("Testing session creation with mobile configuration and lock resolution...")

	// Initialize the AgentBay client
	agentBay, err := agentbay.NewAgentBay(apiKey, nil)
	if err != nil {
		t.Fatalf("Failed to initialize AgentBay client: %v", err)
	}

	// Create mobile configuration with app manager rule and lock resolution
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

	// Create session parameters with mobile_latest image
	params := agentbay.NewCreateSessionParams().
		WithImageId("mobile_latest"). // Specify mobile image
		WithLabels(map[string]string{
			"test_type":  "mobile_config_integration",
			"created_by": "integration_test",
		}).
		WithExtraConfigs(extraConfigs)

	// Create session
	fmt.Println("Creating a new mobile session with extra configs...")
	result, err := agentBay.Create(params)
	if err != nil {
		t.Fatalf("Failed to create session: %v", err)
	}
	session := result.Session
	fmt.Printf("Mobile session created with ID: %s\n", session.SessionID)

	// Verify session properties
	if session.SessionID == "" {
		t.Error("Expected session ID to be set")
	}

	// Clean up
	fmt.Println("Deleting mobile session...")
	deleteResult, err := session.Delete()
	if err != nil {
		t.Fatalf("Failed to delete session: %v", err)
	}
	fmt.Printf("Mobile session deleted (RequestID: %s)\n", deleteResult.RequestID)
}

func TestSessionExtraConfigsIntegration_ExtraConfigsJSONSerialization(t *testing.T) {
	// Get API Key
	apiKey := os.Getenv("AGENTBAY_API_KEY")
	if apiKey == "" {
		t.Fatal("AGENTBAY_API_KEY environment variable is not set")
	}

	fmt.Println("Testing extra configs JSON serialization in real session creation...")

	// Initialize the AgentBay client
	agentBay, err := agentbay.NewAgentBay(apiKey, nil)
	if err != nil {
		t.Fatalf("Failed to initialize AgentBay client: %v", err)
	}

	// Create mobile configuration with lock resolution
	appRule := &models.AppManagerRule{
		RuleType: "White",
		AppPackageNameList: []string{
			"com.android.settings",
			"com.google.android.gms",
			"com.android.systemui",
		},
	}
	mobileConfig := &models.MobileExtraConfig{
		LockResolution: true,
		AppManagerRule: appRule,
	}
	extraConfigs := &models.ExtraConfigs{
		Mobile: mobileConfig,
	}

	// Test JSON serialization before session creation
	jsonStr, err := extraConfigs.ToJSON()
	if err != nil {
		t.Fatalf("Failed to serialize extra configs to JSON: %v", err)
	}
	fmt.Printf("Extra configs JSON: %s\n", jsonStr)

	// Verify JSON contains expected keys
	if !strings.Contains(jsonStr, "mobile") {
		t.Error("Expected JSON to contain 'mobile' key")
	}
	if !strings.Contains(jsonStr, "lock_resolution") {
		t.Error("Expected JSON to contain 'lock_resolution' key")
	}
	if !strings.Contains(jsonStr, "app_manager_rule") {
		t.Error("Expected JSON to contain 'app_manager_rule' key")
	}

	// Create session parameters
	params := agentbay.NewCreateSessionParams().
		WithImageId("mobile_latest").
		WithLabels(map[string]string{
			"test_type":  "json_serialization_test",
			"created_by": "integration_test",
		}).
		WithExtraConfigs(extraConfigs)

	// Test GetExtraConfigsJSON method on session params
	paramsJSON, err := params.GetExtraConfigsJSON()
	if err != nil {
		t.Fatalf("Failed to get extra configs JSON from session params: %v", err)
	}
	fmt.Printf("Session params extra configs JSON: %s\n", paramsJSON)

	// Create session
	fmt.Println("Creating a new session for JSON serialization test...")
	result, err := agentBay.Create(params)
	if err != nil {
		t.Fatalf("Failed to create session: %v", err)
	}
	session := result.Session
	fmt.Printf("JSON serialization test session created with ID: %s\n", session.SessionID)

	// Clean up
	fmt.Println("Deleting JSON serialization test session...")
	deleteResult, err := session.Delete()
	if err != nil {
		t.Fatalf("Failed to delete session: %v", err)
	}
	fmt.Printf("JSON serialization test session deleted (RequestID: %s)\n", deleteResult.RequestID)
}
