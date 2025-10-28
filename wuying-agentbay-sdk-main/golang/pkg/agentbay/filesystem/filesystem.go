package filesystem

import (
	"encoding/json"
	"fmt"
	"strconv"
	"strings"
	"sync"
	"time"

	mcp "github.com/aliyun/wuying-agentbay-sdk/golang/api/client"
	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/models"
)

// FileChangeEvent represents a single file change event
type FileChangeEvent struct {
	EventType string `json:"eventType"` // "create", "modify", "delete"
	Path      string `json:"path"`
	PathType  string `json:"pathType"` // "file", "directory"
}

// String returns string representation of FileChangeEvent
func (e *FileChangeEvent) String() string {
	return fmt.Sprintf("FileChangeEvent(eventType='%s', path='%s', pathType='%s')",
		e.EventType, e.Path, e.PathType)
}

// ToDict converts FileChangeEvent to map
func (e *FileChangeEvent) ToDict() map[string]string {
	return map[string]string{
		"eventType": e.EventType,
		"path":      e.Path,
		"pathType":  e.PathType,
	}
}

// FileChangeEventFromDict creates FileChangeEvent from map
func FileChangeEventFromDict(data map[string]interface{}) *FileChangeEvent {
	event := &FileChangeEvent{}
	if eventType, ok := data["eventType"].(string); ok {
		event.EventType = eventType
	}
	if path, ok := data["path"].(string); ok {
		event.Path = path
	}
	if pathType, ok := data["pathType"].(string); ok {
		event.PathType = pathType
	}
	return event
}

// FileChangeResult wraps file change detection result
type FileChangeResult struct {
	models.ApiResponse
	Events  []*FileChangeEvent
	RawData string
}

// HasChanges checks if there are any file changes
func (r *FileChangeResult) HasChanges() bool {
	return len(r.Events) > 0
}

// GetModifiedFiles returns list of modified file paths
func (r *FileChangeResult) GetModifiedFiles() []string {
	var files []string
	for _, event := range r.Events {
		if event.EventType == "modify" && event.PathType == "file" {
			files = append(files, event.Path)
		}
	}
	return files
}

// GetCreatedFiles returns list of created file paths
func (r *FileChangeResult) GetCreatedFiles() []string {
	var files []string
	for _, event := range r.Events {
		if event.EventType == "create" && event.PathType == "file" {
			files = append(files, event.Path)
		}
	}
	return files
}

// GetDeletedFiles returns list of deleted file paths
func (r *FileChangeResult) GetDeletedFiles() []string {
	var files []string
	for _, event := range r.Events {
		if event.EventType == "delete" && event.PathType == "file" {
			files = append(files, event.Path)
		}
	}
	return files
}

// FileReadResult wraps file read operation result and RequestID
type FileReadResult struct {
	models.ApiResponse // Embedded ApiResponse
	Content            string
}

// FileWriteResult wraps file write operation result and RequestID
type FileWriteResult struct {
	models.ApiResponse // Embedded ApiResponse
	Success            bool
}

// FileExistsResult wraps file existence check result and RequestID
type FileExistsResult struct {
	models.ApiResponse
	Exists bool
}

// FileDirectoryResult wraps directory operation result and RequestID
type FileDirectoryResult struct {
	models.ApiResponse // Embedded ApiResponse
	Success            bool
}

// DirectoryListResult wraps directory listing result and RequestID
type DirectoryListResult struct {
	models.ApiResponse
	Entries []*DirectoryEntry
}

// FileInfoResult wraps file info result and RequestID
type FileInfoResult struct {
	models.ApiResponse
	FileInfo *FileInfo
}

// SearchFilesResult wraps file search result and RequestID
type SearchFilesResult struct {
	models.ApiResponse
	Results []string
}

// FileSystem handles file system operations in the AgentBay cloud environment.
type FileSystem struct {
	Session interface {
		GetAPIKey() string
		GetClient() *mcp.Client
		GetSessionId() string
		IsVpc() bool
		NetworkInterfaceIp() string
		HttpPort() string
		FindServerForTool(toolName string) string
		CallMcpTool(toolName string, args interface{}) (*models.McpToolResult, error)
	}
}

// FileInfo represents file or directory information
type FileInfo struct {
	Name        string `json:"name"`
	Path        string `json:"path"`
	Size        int64  `json:"size"`
	IsDirectory bool   `json:"isDirectory"`
	ModTime     string `json:"modTime"`
	Mode        string `json:"mode"`
	Owner       string `json:"owner,omitempty"`
	Group       string `json:"group,omitempty"`
}

// DirectoryEntry represents a directory entry
type DirectoryEntry struct {
	Name        string `json:"name"`
	IsDirectory bool   `json:"isDirectory"`
}

// Helper function to parse file info from string
func parseFileInfo(fileInfoStr string) (*FileInfo, error) {
	fileInfo := &FileInfo{}
	lines := strings.Split(fileInfoStr, "\n")

	for _, line := range lines {
		if strings.Contains(line, ":") {
			parts := strings.SplitN(line, ":", 2)
			if len(parts) == 2 {
				key := strings.TrimSpace(parts[0])
				value := strings.TrimSpace(parts[1])

				switch key {
				case "size":
					if err := json.Unmarshal([]byte(value), &fileInfo.Size); err == nil {
						// Successfully parsed as number
					} else if size, err := strconv.ParseInt(value, 10, 64); err == nil {
						fileInfo.Size = size
					}
				case "isDirectory":
					if value == "true" {
						fileInfo.IsDirectory = true
					} else if value == "false" {
						fileInfo.IsDirectory = false
					}
				case "permissions":
					fileInfo.Mode = value
				case "modified":
					fileInfo.ModTime = value
				}
			}
		}
	}

	return fileInfo, nil
}

// Helper function to parse directory listing from string
func parseDirectoryListing(text string) ([]*DirectoryEntry, error) {
	var entries []*DirectoryEntry
	lines := strings.Split(text, "\n")

	for _, line := range lines {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}

		var isDirectory bool
		var name string

		if strings.HasPrefix(line, "[DIR] ") {
			isDirectory = true
			name = strings.TrimSpace(line[6:]) // Remove "[DIR] " prefix
		} else if strings.HasPrefix(line, "[FILE] ") {
			isDirectory = false
			name = strings.TrimSpace(line[7:]) // Remove "[FILE] " prefix
		} else {
			// Skip lines that don't match expected format
			continue
		}

		if name != "" {
			entries = append(entries, &DirectoryEntry{
				Name:        name,
				IsDirectory: isDirectory,
			})
		}
	}

	return entries, nil
}

// NewFileSystem creates a new FileSystem instance
func NewFileSystem(session interface {
	GetAPIKey() string
	GetClient() *mcp.Client
	GetSessionId() string
	IsVpc() bool
	NetworkInterfaceIp() string
	HttpPort() string
	FindServerForTool(toolName string) string
	CallMcpTool(toolName string, args interface{}) (*models.McpToolResult, error)
}) *FileSystem {
	return &FileSystem{
		Session: session,
	}
}

// CreateDirectory creates a new directory.
func (fs *FileSystem) CreateDirectory(path string) (*FileDirectoryResult, error) {
	args := map[string]string{
		"path": path,
	}

	result, err := fs.Session.CallMcpTool("create_directory", args)
	if err != nil {
		return nil, fmt.Errorf("failed to create directory: %w", err)
	}

	if !result.Success {
		return nil, fmt.Errorf("create directory failed: %s", result.ErrorMessage)
	}

	return &FileDirectoryResult{
		ApiResponse: models.ApiResponse{
			RequestID: result.RequestID,
		},
		Success: true,
	}, nil
}

// EditFile edits a file with specified changes.
func (fs *FileSystem) EditFile(path string, edits []map[string]string, dryRun bool) (*FileWriteResult, error) {
	args := map[string]interface{}{
		"path":    path,
		"edits":   edits,
		"dry_run": dryRun,
	}

	result, err := fs.Session.CallMcpTool("edit_file", args)
	if err != nil {
		return nil, fmt.Errorf("failed to edit file: %w", err)
	}

	if !result.Success {
		return nil, fmt.Errorf("edit file failed: %s", result.ErrorMessage)
	}

	return &FileWriteResult{
		ApiResponse: models.ApiResponse{
			RequestID: result.RequestID,
		},
		Success: true,
	}, nil
}

// GetFileInfo gets information about a file or directory.
func (fs *FileSystem) GetFileInfo(path string) (*FileInfoResult, error) {
	args := map[string]string{
		"path": path,
	}

	result, err := fs.Session.CallMcpTool("get_file_info", args)
	if err != nil {
		// Check if it's a "file not found" error
		if strings.Contains(err.Error(), "No such file or directory") {
			return nil, fmt.Errorf("file not found: %s", path)
		}
		return nil, fmt.Errorf("failed to get file info: %w", err)
	}

	if !result.Success {
		return nil, fmt.Errorf("get file info failed: %s", result.ErrorMessage)
	}

	fileInfo, err := parseFileInfo(result.Data)
	if err != nil {
		return nil, fmt.Errorf("error parsing file info: %w", err)
	}

	return &FileInfoResult{
		ApiResponse: models.ApiResponse{
			RequestID: result.RequestID,
		},
		FileInfo: fileInfo,
	}, nil
}

// ListDirectory lists the contents of a directory.
func (fs *FileSystem) ListDirectory(path string) (*DirectoryListResult, error) {
	args := map[string]string{
		"path": path,
	}

	result, err := fs.Session.CallMcpTool("list_directory", args)
	if err != nil {
		return nil, fmt.Errorf("failed to list directory: %w", err)
	}

	if !result.Success {
		return nil, fmt.Errorf("list directory failed: %s", result.ErrorMessage)
	}

	entries, err := parseDirectoryListing(result.Data)
	if err != nil {
		return nil, fmt.Errorf("error parsing directory listing: %w", err)
	}

	return &DirectoryListResult{
		ApiResponse: models.ApiResponse{
			RequestID: result.RequestID,
		},
		Entries: entries,
	}, nil
}

// MoveFile moves a file or directory from source to destination.
func (fs *FileSystem) MoveFile(source, destination string) (*FileWriteResult, error) {
	args := map[string]string{
		"source":      source,
		"destination": destination,
	}

	result, err := fs.Session.CallMcpTool("move_file", args)
	if err != nil {
		return nil, fmt.Errorf("failed to move file: %w", err)
	}

	if !result.Success {
		return nil, fmt.Errorf("move file failed: %s", result.ErrorMessage)
	}

	return &FileWriteResult{
		ApiResponse: models.ApiResponse{
			RequestID: result.RequestID,
		},
		Success: true,
	}, nil
}

// readFileChunk reads a file chunk. Internal method used for chunked file operations.
func (fs *FileSystem) readFileChunk(path string, optionalParams ...int) (*FileReadResult, error) {
	// Handle optional parameters for backward compatibility
	offset, length := 0, 0
	if len(optionalParams) > 0 {
		offset = optionalParams[0]
	}
	if len(optionalParams) > 1 {
		length = optionalParams[1]
	}

	args := map[string]interface{}{
		"path": path,
	}
	if offset > 0 {
		args["offset"] = offset
	}
	if length > 0 {
		args["length"] = length
	}

	result, err := fs.Session.CallMcpTool("read_file", args)
	if err != nil {
		return nil, fmt.Errorf("failed to read file: %w", err)
	}

	if !result.Success {
		return nil, fmt.Errorf("read file failed: %s", result.ErrorMessage)
	}

	return &FileReadResult{
		ApiResponse: models.ApiResponse{
			RequestID: result.RequestID,
		},
		Content: result.Data,
	}, nil
}

// ReadMultipleFiles reads multiple files and returns their contents as a map.
func (fs *FileSystem) ReadMultipleFiles(paths []string) (map[string]string, error) {
	args := map[string]interface{}{
		"paths": paths,
	}

	result, err := fs.Session.CallMcpTool("read_multiple_files", args)
	if err != nil {
		return nil, fmt.Errorf("failed to read multiple files: %w", err)
	}

	if !result.Success {
		return nil, fmt.Errorf("read multiple files failed: %s", result.ErrorMessage)
	}

	// Parse the result - format is "path:\ncontent\n\n---\npath2:\ncontent2"
	fileContents := make(map[string]string)
	sections := strings.Split(result.Data, "\n---\n")

	for _, section := range sections {
		section = strings.TrimSpace(section)
		if section == "" {
			continue
		}

		lines := strings.Split(section, "\n")
		if len(lines) < 2 {
			continue
		}

		// First line should be "path:"
		pathLine := strings.TrimSpace(lines[0])
		if !strings.HasSuffix(pathLine, ":") {
			continue
		}

		filePath := strings.TrimSuffix(pathLine, ":")

		// Remaining lines are the content
		contentLines := lines[1:]
		content := strings.Join(contentLines, "\n")

		fileContents[filePath] = content
	}

	return fileContents, nil
}

// SearchFiles searches for files matching a pattern.
func (fs *FileSystem) SearchFiles(path, pattern string, excludePatterns []string) (*SearchFilesResult, error) {
	args := map[string]interface{}{
		"path":             path,
		"pattern":          pattern,
		"exclude_patterns": excludePatterns,
	}

	result, err := fs.Session.CallMcpTool("search_files", args)
	if err != nil {
		return nil, fmt.Errorf("failed to search files: %w", err)
	}

	if !result.Success {
		return nil, fmt.Errorf("search files failed: %s", result.ErrorMessage)
	}

	// Parse the result
	var results []string
	for _, line := range strings.Split(result.Data, "\n") {
		line = strings.TrimSpace(line)
		if line != "" {
			results = append(results, line)
		}
	}

	return &SearchFilesResult{
		ApiResponse: models.ApiResponse{
			RequestID: result.RequestID,
		},
		Results: results,
	}, nil
}

// writeFileChunk writes a file chunk. Internal method used for chunked file operations.
func (fs *FileSystem) writeFileChunk(path, content string, mode string) (*FileWriteResult, error) {
	// Validate mode parameter
	if mode != "" && mode != "overwrite" && mode != "append" {
		return nil, fmt.Errorf("invalid write mode: %s. Must be 'overwrite' or 'append'", mode)
	}

	args := map[string]interface{}{
		"path":    path,
		"content": content,
	}
	if mode != "" {
		args["mode"] = mode
	}

	result, err := fs.Session.CallMcpTool("write_file", args)
	if err != nil {
		return nil, fmt.Errorf("failed to write file: %w", err)
	}

	if !result.Success {
		return nil, fmt.Errorf("write file failed: %s", result.ErrorMessage)
	}

	return &FileWriteResult{
		ApiResponse: models.ApiResponse{
			RequestID: result.RequestID,
		},
		Success: true,
	}, nil
}

// ChunkSize is the default size of chunks for large file operations (50KB)
const ChunkSize = 50 * 1024

// ReadFile reads the contents of a file. Automatically handles large files by chunking.
func (fs *FileSystem) ReadFile(path string) (*FileReadResult, error) {
	chunkSize := ChunkSize

	// First get the file size
	fileInfoResult, err := fs.GetFileInfo(path)
	if err != nil {
		return nil, fmt.Errorf("failed to get file info: %w", err)
	}

	// Get size from the fileInfo struct
	size := fileInfoResult.FileInfo.Size

	if size == 0 {
		return nil, fmt.Errorf("couldn't determine file size")
	}

	// Prepare to read the file in chunks
	var result strings.Builder
	offset := 0
	fileSize := int(size)

	fmt.Printf("ReadFile: Starting chunked read of %s (total size: %d bytes, chunk size: %d bytes)\n",
		path, fileSize, chunkSize)

	chunkCount := 0
	var lastRequestID string
	for offset < fileSize {
		// Calculate how much to read in this chunk
		length := chunkSize
		if offset+length > fileSize {
			length = fileSize - offset
		}

		fmt.Printf("ReadFile: Reading chunk %d (%d bytes at offset %d/%d)\n",
			chunkCount+1, length, offset, fileSize)

		// Read the chunk
		chunkResult, err := fs.readFileChunk(path, offset, length)
		if err != nil {
			return nil, fmt.Errorf("error reading chunk at offset %d: %w", offset, err)
		}

		// Append the chunk text
		result.WriteString(chunkResult.Content)
		lastRequestID = chunkResult.RequestID

		// Move to the next chunk
		offset += length
		chunkCount++
	}

	fmt.Printf("ReadFile: Successfully read %s in %d chunks (total: %d bytes)\n",
		path, chunkCount, fileSize)

	return &FileReadResult{
		ApiResponse: models.ApiResponse{
			RequestID: lastRequestID,
		},
		Content: result.String(),
	}, nil
}

// WriteFile writes content to a file. Automatically handles large files by chunking.
func (fs *FileSystem) WriteFile(path, content string, mode string) (*FileWriteResult, error) {
	chunkSize := ChunkSize
	contentLen := len(content)

	fmt.Printf("WriteFile: Starting write to %s (total size: %d bytes, chunk size: %d bytes)\n",
		path, contentLen, chunkSize)

	// If content is small enough, use the regular writeFileChunk method
	if contentLen <= chunkSize {
		fmt.Printf("WriteFile: Content size (%d bytes) is smaller than chunk size, using normal writeFileChunk\n",
			contentLen)
		return fs.writeFileChunk(path, content, mode)
	}

	// Write the first chunk with the specified mode
	firstChunkEnd := chunkSize
	if firstChunkEnd > contentLen {
		firstChunkEnd = contentLen
	}

	fmt.Printf("WriteFile: Writing first chunk (0-%d bytes) with %s mode\n", firstChunkEnd, mode)
	result, err := fs.writeFileChunk(path, content[:firstChunkEnd], mode)
	if err != nil {
		return nil, fmt.Errorf("error writing first chunk: %w", err)
	}

	// Write the remaining chunks with "append" mode
	chunkCount := 1 // Already wrote first chunk
	for offset := firstChunkEnd; offset < contentLen; {
		end := offset + chunkSize
		if end > contentLen {
			end = contentLen
		}

		fmt.Printf("WriteFile: Writing chunk %d (%d-%d bytes) with append mode\n",
			chunkCount+1, offset, end)

		result, err = fs.writeFileChunk(path, content[offset:end], "append")
		if err != nil {
			return nil, fmt.Errorf("error writing chunk at offset %d: %w", offset, err)
		}

		offset = end
		chunkCount++
	}

	fmt.Printf("WriteFile: Successfully wrote %s in %d chunks (total: %d bytes)\n",
		path, chunkCount, contentLen)

	return result, nil
}

// parseFileChangeData parses raw JSON data into FileChangeEvent slice
func parseFileChangeData(rawData string) ([]*FileChangeEvent, error) {
	var events []*FileChangeEvent
	var changeData []map[string]interface{}

	if err := json.Unmarshal([]byte(rawData), &changeData); err != nil {
		return events, fmt.Errorf("failed to parse JSON: %w", err)
	}

	for _, eventDict := range changeData {
		event := FileChangeEventFromDict(eventDict)
		events = append(events, event)
	}

	return events, nil
}

// GetFileChange gets file change information for the specified directory path
func (fs *FileSystem) GetFileChange(path string) (*FileChangeResult, error) {
	args := map[string]string{
		"path": path,
	}

	result, err := fs.Session.CallMcpTool("get_file_change", args)
	if err != nil {
		return nil, fmt.Errorf("failed to get file change: %w", err)
	}

	if !result.Success {
		return &FileChangeResult{
			ApiResponse: models.ApiResponse{
				RequestID: result.RequestID,
			},
			RawData: result.Data,
		}, fmt.Errorf("get file change failed: %s", result.ErrorMessage)
	}

	// Parse the file change events
	events, err := parseFileChangeData(result.Data)
	if err != nil {
		return &FileChangeResult{
			ApiResponse: models.ApiResponse{
				RequestID: result.RequestID,
			},
			RawData: result.Data,
		}, fmt.Errorf("failed to parse file change data: %w", err)
	}

	return &FileChangeResult{
		ApiResponse: models.ApiResponse{
			RequestID: result.RequestID,
		},
		Events:  events,
		RawData: result.Data,
	}, nil
}

// WatchDirectoryWithDefaults watches a directory for file changes with default 500ms polling interval
func (fs *FileSystem) WatchDirectoryWithDefaults(
	path string,
	callback func([]*FileChangeEvent),
	stopCh <-chan struct{},
) *sync.WaitGroup {
	return fs.WatchDirectory(path, callback, 500*time.Millisecond, stopCh)
}

// WatchDirectory watches a directory for file changes and calls the callback function when changes occur
func (fs *FileSystem) WatchDirectory(
	path string,
	callback func([]*FileChangeEvent),
	interval time.Duration,
	stopCh <-chan struct{},
) *sync.WaitGroup {
	var wg sync.WaitGroup
	wg.Add(1)

	go func() {
		defer wg.Done()
		fmt.Printf("Starting directory monitoring for: %s\n", path)
		fmt.Printf("Polling interval: %v\n", interval)

		ticker := time.NewTicker(interval)
		defer ticker.Stop()

		for {
			select {
			case <-stopCh:
				fmt.Printf("Stopped monitoring directory: %s\n", path)
				return
			case <-ticker.C:
				result, err := fs.GetFileChange(path)
				if err != nil {
					fmt.Printf("Error monitoring directory: %v\n", err)
					continue
				}

				if len(result.Events) > 0 {
					fmt.Printf("Detected %d file changes:\n", len(result.Events))
					for _, event := range result.Events {
						fmt.Printf("  - %s\n", event.String())
					}

					// Call callback in a separate goroutine to avoid blocking
					go func(events []*FileChangeEvent) {
						defer func() {
							if r := recover(); r != nil {
								fmt.Printf("Error in callback function: %v\n", r)
							}
						}()
						callback(events)
					}(result.Events)
				}
			}
		}
	}()

	return &wg
}
