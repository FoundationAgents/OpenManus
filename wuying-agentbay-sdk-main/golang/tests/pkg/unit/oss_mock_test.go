package agentbay_test

import (
	"testing"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/oss"
	"github.com/aliyun/wuying-agentbay-sdk/golang/tests/pkg/unit/mock"
	"github.com/golang/mock/gomock"
	"github.com/stretchr/testify/assert"
)

func TestOSS_EnvInit_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock OSS
	mockOSS := mock.NewMockOSSInterface(ctrl)

	// Set expected behavior
	expectedResult := &oss.EnvInitResult{
		Result: "OSS environment initialized",
	}
	mockOSS.EXPECT().EnvInit("access_key", "secret_key", "security_token", "endpoint.com", "cn-shanghai").Return(expectedResult, nil)

	// Test EnvInit method call
	result, err := mockOSS.EnvInit("access_key", "secret_key", "security_token", "endpoint.com", "cn-shanghai")

	// Verify call success
	assert.NoError(t, err)
	assert.NotNil(t, result)
	assert.Equal(t, "OSS environment initialized", result.Result)
}

func TestOSS_Upload_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock OSS
	mockOSS := mock.NewMockOSSInterface(ctrl)

	// Set expected behavior
	expectedResult := &oss.UploadResult{
		URL: "http://example.com/uploaded-file",
	}
	mockOSS.EXPECT().Upload("test-bucket", "test-object", "/local/path").Return(expectedResult, nil)

	// Test Upload method call
	result, err := mockOSS.Upload("test-bucket", "test-object", "/local/path")

	// Verify call success
	assert.NoError(t, err)
	assert.NotNil(t, result)
	assert.Equal(t, "http://example.com/uploaded-file", result.URL)
}

func TestOSS_UploadAnonymous_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock OSS
	mockOSS := mock.NewMockOSSInterface(ctrl)

	// Set expected behavior
	expectedResult := &oss.UploadResult{
		URL: "http://example.com/anonymous-upload",
	}
	mockOSS.EXPECT().UploadAnonymous("http://example.com/upload", "/local/path").Return(expectedResult, nil)

	// Test UploadAnonymous method call
	result, err := mockOSS.UploadAnonymous("http://example.com/upload", "/local/path")

	// Verify call success
	assert.NoError(t, err)
	assert.NotNil(t, result)
	assert.Equal(t, "http://example.com/anonymous-upload", result.URL)
}

func TestOSS_Download_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock OSS
	mockOSS := mock.NewMockOSSInterface(ctrl)

	// Set expected behavior
	expectedResult := &oss.DownloadResult{
		LocalPath: "/local/downloaded-file",
	}
	mockOSS.EXPECT().Download("test-bucket", "test-object", "/local/path").Return(expectedResult, nil)

	// Test Download method call
	result, err := mockOSS.Download("test-bucket", "test-object", "/local/path")

	// Verify call success
	assert.NoError(t, err)
	assert.NotNil(t, result)
	assert.Equal(t, "/local/downloaded-file", result.LocalPath)
}

func TestOSS_DownloadAnonymous_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock OSS
	mockOSS := mock.NewMockOSSInterface(ctrl)

	// Set expected behavior
	expectedResult := &oss.DownloadResult{
		LocalPath: "/local/anonymous-download",
	}
	mockOSS.EXPECT().DownloadAnonymous("http://example.com/download", "/local/path").Return(expectedResult, nil)

	// Test DownloadAnonymous method call
	result, err := mockOSS.DownloadAnonymous("http://example.com/download", "/local/path")

	// Verify call success
	assert.NoError(t, err)
	assert.NotNil(t, result)
	assert.Equal(t, "/local/anonymous-download", result.LocalPath)
}

func TestOSS_Error_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock OSS
	mockOSS := mock.NewMockOSSInterface(ctrl)

	// Set expected behavior - return error
	mockOSS.EXPECT().EnvInit("invalid", "credentials", "", "wrong.endpoint", "invalid-region").Return(nil, assert.AnError)

	// Test error case
	result, err := mockOSS.EnvInit("invalid", "credentials", "", "wrong.endpoint", "invalid-region")

	// Verify error handling
	assert.Error(t, err)
	assert.Nil(t, result)
}
