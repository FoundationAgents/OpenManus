package agentbay_test

import (
	"testing"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/filesystem"
	"github.com/aliyun/wuying-agentbay-sdk/golang/tests/pkg/unit/mock"
	"github.com/golang/mock/gomock"
	"github.com/stretchr/testify/assert"
)

func TestFileSystem_ReadFile_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock FileSystem
	mockFS := mock.NewMockFileSystemInterface(ctrl)

	// Set expected behavior
	expectedResult := &filesystem.FileReadResult{
		Content: "file content",
	}
	mockFS.EXPECT().ReadFile("/test/file.txt").Return(expectedResult, nil)

	// Test ReadFile method call
	result, err := mockFS.ReadFile("/test/file.txt")

	// Verify call success
	assert.NoError(t, err)
	assert.NotNil(t, result)
	assert.Equal(t, "file content", result.Content)
}

func TestFileSystem_CreateDirectory_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock FileSystem
	mockFS := mock.NewMockFileSystemInterface(ctrl)

	// Set expected behavior
	expectedResult := &filesystem.FileDirectoryResult{
		Success: true,
	}
	mockFS.EXPECT().CreateDirectory("/test/dir").Return(expectedResult, nil)

	// Test CreateDirectory method call
	result, err := mockFS.CreateDirectory("/test/dir")

	// Verify call success
	assert.NoError(t, err)
	assert.NotNil(t, result)
	assert.True(t, result.Success)
}

func TestFileSystem_EditFile_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock FileSystem
	mockFS := mock.NewMockFileSystemInterface(ctrl)

	// Set expected behavior
	expectedResult := &filesystem.FileWriteResult{Success: true}
	edits := []map[string]string{{"oldText": "old", "newText": "new content"}}
	mockFS.EXPECT().EditFile("/test/file.txt", edits, false).Return(expectedResult, nil)

	// Test EditFile method call
	result, err := mockFS.EditFile("/test/file.txt", edits, false)

	// Verify call success
	assert.NoError(t, err)
	assert.NotNil(t, result)
	assert.True(t, result.Success)
}

func TestFileSystem_WriteFile_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock FileSystem
	mockFS := mock.NewMockFileSystemInterface(ctrl)

	// Set expected behavior
	expectedResult := &filesystem.FileWriteResult{Success: true}
	mockFS.EXPECT().WriteFile("/test/file.txt", "content", "overwrite").Return(expectedResult, nil)

	// Test WriteFile method call
	result, err := mockFS.WriteFile("/test/file.txt", "content", "overwrite")

	// Verify call success
	assert.NoError(t, err)
	assert.NotNil(t, result)
	assert.True(t, result.Success)
}

func TestFileSystem_Error_WithMockClient(t *testing.T) {
	ctrl := gomock.NewController(t)
	defer ctrl.Finish()

	// Create mock FileSystem
	mockFS := mock.NewMockFileSystemInterface(ctrl)

	// Set expected behavior - return error
	mockFS.EXPECT().ReadFile("/test/file.txt").Return(nil, assert.AnError)

	// Test error case
	result, err := mockFS.ReadFile("/test/file.txt")

	// Verify error handling
	assert.Error(t, err)
	assert.Nil(t, result)
}
