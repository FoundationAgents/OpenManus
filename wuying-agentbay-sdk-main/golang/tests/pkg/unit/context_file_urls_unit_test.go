package agentbay_test

import (
	"testing"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
	interfaces "github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/interface"
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/models"
	"github.com/stretchr/testify/assert"
)

// fakeContext is a simple fake implementing interfaces.ContextInterface for unit tests
type fakeContext struct {
	uploadURLRes   *agentbay.ContextFileUrlResult
	downloadURLRes *agentbay.ContextFileUrlResult
	listFilesRes   *agentbay.ContextFileListResult
	deleteFileRes  *agentbay.ContextFileDeleteResult
}

// File URL APIs
func (f *fakeContext) GetFileUploadUrl(contextID string, filePath string) (*agentbay.ContextFileUrlResult, error) {
	return f.uploadURLRes, nil
}

func (f *fakeContext) GetFileDownloadUrl(contextID string, filePath string) (*agentbay.ContextFileUrlResult, error) {
	return f.downloadURLRes, nil
}

func (f *fakeContext) ListFiles(contextID string, parentFolderPath string, pageNumber int32, pageSize int32) (*agentbay.ContextFileListResult, error) {
	return f.listFilesRes, nil
}

func (f *fakeContext) DeleteFile(contextID string, filePath string) (*agentbay.ContextFileDeleteResult, error) {
	return f.deleteFileRes, nil
}

// Other methods to satisfy interfaces.ContextInterface (not used in these tests)
func (f *fakeContext) List(params *agentbay.ContextListParams) (*agentbay.ContextListResult, error) {
	return nil, nil
}
func (f *fakeContext) Get(name string, create bool) (*agentbay.ContextResult, error) { return nil, nil }
func (f *fakeContext) Create(name string) (*agentbay.ContextCreateResult, error)     { return nil, nil }
func (f *fakeContext) Update(context *agentbay.Context) (*agentbay.ContextModifyResult, error) {
	return nil, nil
}
func (f *fakeContext) Delete(context *agentbay.Context) (*agentbay.ContextDeleteResult, error) {
	return nil, nil
}

// Helper to get a ContextInterface from fake
func newFakeContext(fc *fakeContext) interfaces.ContextInterface { return fc }

func TestContext_GetFileUploadUrl_Unit(t *testing.T) {
	// Arrange
	expire := int64(3600)
	fake := newFakeContext(&fakeContext{
		uploadURLRes: &agentbay.ContextFileUrlResult{
			ApiResponse: models.WithRequestID("req-upload-1"),
			Success:     true,
			Url:         "https://oss.example.com/upload-url",
			ExpireTime:  &expire,
		},
	})

	// Act
	res, err := fake.GetFileUploadUrl("ctx-123", "/tmp/integration_upload_test.txt")

	// Assert
	assert.NoError(t, err)
	assert.NotNil(t, res)
	assert.True(t, res.Success)
	assert.Equal(t, "https://oss.example.com/upload-url", res.Url)
	if assert.NotNil(t, res.ExpireTime) {
		assert.Equal(t, int64(3600), *res.ExpireTime)
	}
}

func TestContext_GetFileDownloadUrl_Unit(t *testing.T) {
	// Arrange
	expire := int64(7200)
	fake := newFakeContext(&fakeContext{
		downloadURLRes: &agentbay.ContextFileUrlResult{
			ApiResponse: models.WithRequestID("req-download-1"),
			Success:     true,
			Url:         "https://oss.example.com/download-url",
			ExpireTime:  &expire,
		},
	})

	// Act
	res, err := fake.GetFileDownloadUrl("ctx-123", "/tmp/integration_upload_test.txt")

	// Assert
	assert.NoError(t, err)
	assert.NotNil(t, res)
	assert.True(t, res.Success)
	assert.Equal(t, "https://oss.example.com/download-url", res.Url)
	if assert.NotNil(t, res.ExpireTime) {
		assert.Equal(t, int64(7200), *res.ExpireTime)
	}
}

func TestContext_GetFileDownloadUrl_Unit_Unavailable(t *testing.T) {
	// Arrange
	fake := newFakeContext(&fakeContext{
		downloadURLRes: &agentbay.ContextFileUrlResult{
			ApiResponse: models.WithRequestID("req-download-2"),
			Success:     false,
			Url:         "",
			ExpireTime:  nil,
		},
	})

	// Act
	res, err := fake.GetFileDownloadUrl("ctx-123", "/tmp/integration_upload_test.txt")

	// Assert
	assert.NoError(t, err)
	assert.NotNil(t, res)
	assert.False(t, res.Success)
	assert.Equal(t, "", res.Url)
	assert.Nil(t, res.ExpireTime)
}

func TestContext_ListFiles_Unit_WithEntry(t *testing.T) {
	// Arrange
	entries := []*agentbay.ContextFileEntry{
		{
			FileID:   "fid-1",
			FileName: "integration_upload_test.txt",
			FilePath: "/tmp/integration_upload_test.txt",
			Size:     21,
			Status:   "ready",
		},
	}
	count := int32(1)
	fake := newFakeContext(&fakeContext{
		listFilesRes: &agentbay.ContextFileListResult{
			ApiResponse: models.WithRequestID("req-list-1"),
			Success:     true,
			Entries:     entries,
			Count:       &count,
		},
	})

	// Act
	res, err := fake.ListFiles("ctx-123", "/tmp", 1, 50)

	// Assert
	assert.NoError(t, err)
	assert.NotNil(t, res)
	assert.True(t, res.Success)
	assert.Equal(t, 1, len(res.Entries))
	assert.Equal(t, "/tmp/integration_upload_test.txt", res.Entries[0].FilePath)
	if assert.NotNil(t, res.Count) {
		assert.Equal(t, int32(1), *res.Count)
	}
}

func TestContext_ListFiles_Unit_Empty(t *testing.T) {
	// Arrange
	fake := newFakeContext(&fakeContext{
		listFilesRes: &agentbay.ContextFileListResult{
			ApiResponse: models.WithRequestID("req-list-2"),
			Success:     true,
			Entries:     []*agentbay.ContextFileEntry{},
			Count:       nil,
		},
	})

	// Act
	res, err := fake.ListFiles("ctx-123", "/tmp", 1, 50)

	// Assert
	assert.NoError(t, err)
	assert.NotNil(t, res)
	assert.True(t, res.Success)
	assert.Equal(t, 0, len(res.Entries))
	assert.Nil(t, res.Count)
}

func TestContext_DeleteFile_Unit(t *testing.T) {
	// Arrange
	fake := newFakeContext(&fakeContext{
		deleteFileRes: &agentbay.ContextFileDeleteResult{
			ApiResponse: models.WithRequestID("req-del-1"),
			Success:     true,
		},
	})

	// Act
	res, err := fake.DeleteFile("ctx-123", "/tmp/integration_upload_test.txt")

	// Assert
	assert.NoError(t, err)
	assert.NotNil(t, res)
	assert.True(t, res.Success)
}
