package agentbay_test

import (
	"testing"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/models"
	"github.com/aliyun/wuying-agentbay-sdk/golang/tests/pkg/unit/mock"
	"github.com/golang/mock/gomock"
	"github.com/stretchr/testify/assert"
)

func TestSessionParams_NewCreateSessionParams_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock SessionParams
	mockSessionParams := mock.NewMockSessionParamsInterface(ctrl)

	// Set expected behavior
	expectedResult := &agentbay.CreateSessionParams{
		Labels:      make(map[string]string),
		ContextSync: []*agentbay.ContextSync{},
	}
	mockSessionParams.EXPECT().NewCreateSessionParams().Return(expectedResult)

	// Test NewCreateSessionParams method call
	result := mockSessionParams.NewCreateSessionParams()

	// Verify call success
	assert.NotNil(t, result)
	assert.NotNil(t, result.Labels)
	assert.NotNil(t, result.ContextSync)
}

func TestSessionParams_WithLabels_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock SessionParams
	mockSessionParams := mock.NewMockSessionParamsInterface(ctrl)

	// Set expected behavior
	labels := map[string]string{"env": "test", "version": "1.0"}
	expectedResult := &agentbay.CreateSessionParams{
		Labels: labels,
	}
	mockSessionParams.EXPECT().WithLabels(labels).Return(expectedResult)

	// Test WithLabels method call
	result := mockSessionParams.WithLabels(labels)

	// Verify call success
	assert.NotNil(t, result)
	assert.Equal(t, labels, result.Labels)
}

func TestSessionParams_WithContextID_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock SessionParams
	mockSessionParams := mock.NewMockSessionParamsInterface(ctrl)

	// Set expected behavior
	contextID := "test-context-id"
	expectedResult := &agentbay.CreateSessionParams{}
	mockSessionParams.EXPECT().WithContextID(contextID).Return(expectedResult)

	// Test WithContextID method call
	result := mockSessionParams.WithContextID(contextID)

	// Verify call success
	assert.NotNil(t, result)
}

func TestSessionParams_GetLabelsJSON_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock SessionParams
	mockSessionParams := mock.NewMockSessionParamsInterface(ctrl)

	// Set expected behavior
	expectedJSON := `{"env":"test","version":"1.0"}`
	mockSessionParams.EXPECT().GetLabelsJSON().Return(expectedJSON, nil)

	// Test GetLabelsJSON method call
	result, err := mockSessionParams.GetLabelsJSON()

	// Verify call success
	assert.NoError(t, err)
	assert.Equal(t, expectedJSON, result)
}

func TestSessionParams_AddContextSync_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock SessionParams
	mockSessionParams := mock.NewMockSessionParamsInterface(ctrl)

	// Set expected behavior
	contextID := "test-context"
	path := "/test/path"
	policy := &agentbay.SyncPolicy{
		UploadPolicy: &agentbay.UploadPolicy{AutoUpload: true},
	}
	expectedResult := &agentbay.CreateSessionParams{
		ContextSync: []*agentbay.ContextSync{
			{ContextID: contextID, Path: path, Policy: policy},
		},
	}
	mockSessionParams.EXPECT().AddContextSync(contextID, path, policy).Return(expectedResult)

	// Test AddContextSync method call
	result := mockSessionParams.AddContextSync(contextID, path, policy)

	// Verify call success
	assert.NotNil(t, result)
	assert.Len(t, result.ContextSync, 1)
	assert.Equal(t, contextID, result.ContextSync[0].ContextID)
	assert.Equal(t, path, result.ContextSync[0].Path)
	assert.True(t, result.ContextSync[0].Policy.UploadPolicy.AutoUpload)
}

// Extra Config related tests
func TestSessionParams_WithExtraConfigs(t *testing.T) {
	params := agentbay.NewCreateSessionParams()

	// Create mobile configuration with app manager rule and lock resolution
	appRule := &models.AppManagerRule{
		RuleType:           "White",
		AppPackageNameList: []string{"com.android.settings", "com.example.test.app"},
	}
	mobileConfig := &models.MobileExtraConfig{
		LockResolution: true,
		AppManagerRule: appRule,
	}
	extraConfigs := &models.ExtraConfigs{
		Mobile: mobileConfig,
	}

	// Set extra configs
	params.WithExtraConfigs(extraConfigs)

	assert.NotNil(t, params.ExtraConfigs)
	assert.NotNil(t, params.ExtraConfigs.Mobile)
	assert.True(t, params.ExtraConfigs.Mobile.LockResolution)
	assert.NotNil(t, params.ExtraConfigs.Mobile.AppManagerRule)
	assert.Equal(t, "White", params.ExtraConfigs.Mobile.AppManagerRule.RuleType)
	assert.Equal(t, 2, len(params.ExtraConfigs.Mobile.AppManagerRule.AppPackageNameList))
}

func TestSessionParams_GetExtraConfigsJSON(t *testing.T) {
	params := agentbay.NewCreateSessionParams()

	// Test with nil ExtraConfigs
	jsonStr, err := params.GetExtraConfigsJSON()
	assert.NoError(t, err)
	assert.Equal(t, "", jsonStr)

	// Test with mobile configuration including lock resolution
	appRule := &models.AppManagerRule{
		RuleType: "White",
		AppPackageNameList: []string{
			"com.android.settings",
			"com.example.test.app",
		},
	}
	mobileConfig := &models.MobileExtraConfig{
		LockResolution: true,
		AppManagerRule: appRule,
	}
	extraConfigs := &models.ExtraConfigs{
		Mobile: mobileConfig,
	}
	params.WithExtraConfigs(extraConfigs)

	jsonStr, err = params.GetExtraConfigsJSON()
	assert.NoError(t, err)
	assert.NotEmpty(t, jsonStr)
	assert.Contains(t, jsonStr, "mobile")
	assert.Contains(t, jsonStr, "lock_resolution")
	assert.Contains(t, jsonStr, "app_manager_rule")
}

func TestSessionParams_MethodChaining_WithExtraConfigs(t *testing.T) {
	params := agentbay.NewCreateSessionParams()

	// Create mobile configuration for chaining test with lock resolution
	appRule := &models.AppManagerRule{
		RuleType: "White",
		AppPackageNameList: []string{
			"com.android.settings",
			"com.example.app",
		},
	}
	mobileConfig := &models.MobileExtraConfig{
		LockResolution: true,
		AppManagerRule: appRule,
	}
	extraConfigs := &models.ExtraConfigs{
		Mobile: mobileConfig,
	}

	// Test method chaining
	result := params.
		WithImageId("mobile_latest").
		WithLabels(map[string]string{
			"project":   "mobile-testing",
			"test_type": "extra_config",
		}).
		WithExtraConfigs(extraConfigs)

	// Verify chaining returns the same instance
	assert.Equal(t, params, result)

	// Verify all configurations are set
	assert.Equal(t, "mobile_latest", params.ImageId)
	assert.Equal(t, 2, len(params.Labels))
	assert.NotNil(t, params.ExtraConfigs)
	assert.NotNil(t, params.ExtraConfigs.Mobile)
	assert.True(t, params.ExtraConfigs.Mobile.LockResolution)
}
