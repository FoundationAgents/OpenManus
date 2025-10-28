package agentbay_test

import (
	"sync"
	"testing"
	"time"

	mcp "github.com/aliyun/wuying-agentbay-sdk/golang/api/client"
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/filesystem"
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/models"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/mock"
)

// MockWatchSession for testing watch directory functionality
type MockWatchSession struct {
	mock.Mock
}

func (m *MockWatchSession) GetAPIKey() string {
	args := m.Called()
	return args.String(0)
}

func (m *MockWatchSession) GetClient() *mcp.Client {
	args := m.Called()
	return args.Get(0).(*mcp.Client)
}

func (m *MockWatchSession) GetSessionId() string {
	args := m.Called()
	return args.String(0)
}

func (m *MockWatchSession) IsVpc() bool {
	args := m.Called()
	return args.Bool(0)
}

func (m *MockWatchSession) NetworkInterfaceIp() string {
	args := m.Called()
	return args.String(0)
}

func (m *MockWatchSession) HttpPort() string {
	args := m.Called()
	return args.String(0)
}

func (m *MockWatchSession) FindServerForTool(toolName string) string {
	args := m.Called(toolName)
	return args.String(0)
}

func (m *MockWatchSession) CallMcpTool(toolName string, args interface{}) (*models.McpToolResult, error) {
	mockArgs := m.Called(toolName, args)
	return mockArgs.Get(0).(*models.McpToolResult), mockArgs.Error(1)
}

func TestFileChangeEvent_String(t *testing.T) {
	event := &filesystem.FileChangeEvent{
		EventType: "modify",
		Path:      "/tmp/test.txt",
		PathType:  "file",
	}

	expected := "FileChangeEvent(eventType='modify', path='/tmp/test.txt', pathType='file')"
	assert.Equal(t, expected, event.String())
}

func TestFileChangeEvent_ToDict(t *testing.T) {
	event := &filesystem.FileChangeEvent{
		EventType: "create",
		Path:      "/tmp/new_file.txt",
		PathType:  "file",
	}

	expected := map[string]string{
		"eventType": "create",
		"path":      "/tmp/new_file.txt",
		"pathType":  "file",
	}
	assert.Equal(t, expected, event.ToDict())
}

func TestFileChangeEventFromDict(t *testing.T) {
	data := map[string]interface{}{
		"eventType": "delete",
		"path":      "/tmp/deleted.txt",
		"pathType":  "file",
	}

	event := filesystem.FileChangeEventFromDict(data)

	assert.Equal(t, "delete", event.EventType)
	assert.Equal(t, "/tmp/deleted.txt", event.Path)
	assert.Equal(t, "file", event.PathType)
}

func TestFileChangeEventFromDict_MissingFields(t *testing.T) {
	data := map[string]interface{}{
		"eventType": "create",
	}

	event := filesystem.FileChangeEventFromDict(data)

	assert.Equal(t, "create", event.EventType)
	assert.Equal(t, "", event.Path)
	assert.Equal(t, "", event.PathType)
}

func TestFileChangeResult_HasChanges(t *testing.T) {
	// Test with events
	events := []*filesystem.FileChangeEvent{
		{EventType: "create", Path: "/tmp/file1.txt", PathType: "file"},
	}
	result := &filesystem.FileChangeResult{
		Events: events,
	}
	assert.True(t, result.HasChanges())

	// Test without events
	resultEmpty := &filesystem.FileChangeResult{
		Events: []*filesystem.FileChangeEvent{},
	}
	assert.False(t, resultEmpty.HasChanges())
}

func TestFileChangeResult_GetModifiedFiles(t *testing.T) {
	events := []*filesystem.FileChangeEvent{
		{EventType: "create", Path: "/tmp/file1.txt", PathType: "file"},
		{EventType: "modify", Path: "/tmp/file2.txt", PathType: "file"},
		{EventType: "modify", Path: "/tmp/dir1", PathType: "directory"},
		{EventType: "delete", Path: "/tmp/file3.txt", PathType: "file"},
		{EventType: "modify", Path: "/tmp/file4.txt", PathType: "file"},
	}

	result := &filesystem.FileChangeResult{
		Events: events,
	}

	modifiedFiles := result.GetModifiedFiles()
	expected := []string{"/tmp/file2.txt", "/tmp/file4.txt"}
	assert.Equal(t, expected, modifiedFiles)
}

func TestFileChangeResult_GetCreatedFiles(t *testing.T) {
	events := []*filesystem.FileChangeEvent{
		{EventType: "create", Path: "/tmp/file1.txt", PathType: "file"},
		{EventType: "modify", Path: "/tmp/file2.txt", PathType: "file"},
		{EventType: "create", Path: "/tmp/dir1", PathType: "directory"},
		{EventType: "create", Path: "/tmp/file3.txt", PathType: "file"},
	}

	result := &filesystem.FileChangeResult{
		Events: events,
	}

	createdFiles := result.GetCreatedFiles()
	expected := []string{"/tmp/file1.txt", "/tmp/file3.txt"}
	assert.Equal(t, expected, createdFiles)
}

func TestFileChangeResult_GetDeletedFiles(t *testing.T) {
	events := []*filesystem.FileChangeEvent{
		{EventType: "create", Path: "/tmp/file1.txt", PathType: "file"},
		{EventType: "delete", Path: "/tmp/file2.txt", PathType: "file"},
		{EventType: "delete", Path: "/tmp/dir1", PathType: "directory"},
		{EventType: "delete", Path: "/tmp/file3.txt", PathType: "file"},
	}

	result := &filesystem.FileChangeResult{
		Events: events,
	}

	deletedFiles := result.GetDeletedFiles()
	expected := []string{"/tmp/file2.txt", "/tmp/file3.txt"}
	assert.Equal(t, expected, deletedFiles)
}

func TestFileSystem_GetFileChange_Success(t *testing.T) {
	mockSession := new(MockWatchSession)
	fs := filesystem.NewFileSystem(mockSession)

	// Mock successful response
	mockResult := &models.McpToolResult{
		Success:   true,
		RequestID: "test-123",
		Data: `[
			{"eventType": "create", "path": "/tmp/file1.txt", "pathType": "file"},
			{"eventType": "modify", "path": "/tmp/file2.txt", "pathType": "file"}
		]`,
	}

	mockSession.On("CallMcpTool", "get_file_change", map[string]string{"path": "/tmp/test_dir"}).Return(mockResult, nil)

	// Test the method
	result, err := fs.GetFileChange("/tmp/test_dir")

	assert.NoError(t, err)
	assert.Equal(t, "test-123", result.RequestID)
	assert.Len(t, result.Events, 2)
	assert.Equal(t, "create", result.Events[0].EventType)
	assert.Equal(t, "/tmp/file1.txt", result.Events[0].Path)
	assert.Equal(t, "modify", result.Events[1].EventType)
	assert.Equal(t, "/tmp/file2.txt", result.Events[1].Path)

	mockSession.AssertExpectations(t)
}

func TestFileSystem_GetFileChange_Failure(t *testing.T) {
	mockSession := new(MockWatchSession)
	fs := filesystem.NewFileSystem(mockSession)

	// Mock failed response
	mockResult := &models.McpToolResult{
		Success:      false,
		RequestID:    "test-456",
		ErrorMessage: "Directory not found",
		Data:         "",
	}

	mockSession.On("CallMcpTool", "get_file_change", map[string]string{"path": "/tmp/nonexistent"}).Return(mockResult, nil)

	// Test the method
	result, err := fs.GetFileChange("/tmp/nonexistent")

	assert.Error(t, err)
	assert.Contains(t, err.Error(), "Directory not found")
	assert.Equal(t, "test-456", result.RequestID)
	assert.Len(t, result.Events, 0)

	mockSession.AssertExpectations(t)
}

func TestFileSystem_GetFileChange_InvalidJSON(t *testing.T) {
	mockSession := new(MockWatchSession)
	fs := filesystem.NewFileSystem(mockSession)

	// Mock response with invalid JSON
	mockResult := &models.McpToolResult{
		Success:   true,
		RequestID: "test-789",
		Data:      "invalid json data",
	}

	mockSession.On("CallMcpTool", "get_file_change", map[string]string{"path": "/tmp/test_dir"}).Return(mockResult, nil)

	// Test the method
	result, err := fs.GetFileChange("/tmp/test_dir")

	assert.Error(t, err)
	assert.Contains(t, err.Error(), "failed to parse file change data")
	assert.Equal(t, "test-789", result.RequestID)
	assert.Len(t, result.Events, 0)

	mockSession.AssertExpectations(t)
}

func TestFileSystem_WatchDirectory_Basic(t *testing.T) {
	mockSession := new(MockWatchSession)
	fs := filesystem.NewFileSystem(mockSession)

	callbackEvents := make([]*filesystem.FileChangeEvent, 0)
	var mu sync.Mutex

	callback := func(events []*filesystem.FileChangeEvent) {
		mu.Lock()
		defer mu.Unlock()
		callbackEvents = append(callbackEvents, events...)
	}

	// Mock GetFileChange to return some events
	mockResult := &models.McpToolResult{
		Success:   true,
		RequestID: "test-123",
		Data:      `[{"eventType": "create", "path": "/tmp/test.txt", "pathType": "file"}]`,
	}

	mockSession.On("CallMcpTool", "get_file_change", map[string]string{"path": "/tmp/test_dir"}).Return(mockResult, nil)

	// Start watching
	stopCh := make(chan struct{})
	wg := fs.WatchDirectory(
		"/tmp/test_dir",
		callback,
		100*time.Millisecond, // Very short interval for testing
		stopCh,
	)

	// Let it run briefly
	time.Sleep(200 * time.Millisecond)

	// Stop watching
	close(stopCh)
	wg.Wait()

	// Verify callback was called with events
	mu.Lock()
	defer mu.Unlock()
	assert.Greater(t, len(callbackEvents), 0)
	if len(callbackEvents) > 0 {
		assert.Equal(t, "create", callbackEvents[0].EventType)
		assert.Equal(t, "/tmp/test.txt", callbackEvents[0].Path)
	}

	mockSession.AssertExpectations(t)
}
