package interfaces

import (
	"sync"
	"time"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/filesystem"
)

//go:generate mockgen -destination=../../../tests/pkg/unit/mock/mock_filesystem.go -package=mock github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/interface FileSystemInterface

// FileSystemInterface defines the interface for filesystem operations
type FileSystemInterface interface {
	// ReadFile reads content from a file. Automatically handles large files by chunking.
	ReadFile(path string) (*filesystem.FileReadResult, error)

	// WriteFile writes content to a file. Automatically handles large files by chunking.
	WriteFile(path, content string, mode string) (*filesystem.FileWriteResult, error)

	// EditFile edits a file by replacing occurrences of oldText with newText
	EditFile(path string, edits []map[string]string, dryRun bool) (*filesystem.FileWriteResult, error)

	// CreateDirectory creates a directory
	CreateDirectory(path string) (*filesystem.FileDirectoryResult, error)

	// GetFileInfo gets information about a file or directory
	GetFileInfo(path string) (*filesystem.FileInfoResult, error)

	// ListDirectory lists the contents of a directory
	ListDirectory(path string) (*filesystem.DirectoryListResult, error)

	// MoveFile moves a file or directory from source to destination
	MoveFile(source, destination string) (*filesystem.FileWriteResult, error)

	// ReadMultipleFiles reads the contents of multiple files
	ReadMultipleFiles(paths []string) (map[string]string, error)

	// SearchFiles searches for files matching a pattern in a directory
	SearchFiles(path, pattern string, excludePatterns []string) (*filesystem.SearchFilesResult, error)

	// GetFileChange gets file change information for a directory
	GetFileChange(path string) (*filesystem.FileChangeResult, error)

	// WatchDirectory watches a directory for file changes
	WatchDirectory(path string, callback func([]*filesystem.FileChangeEvent), interval time.Duration, stopCh <-chan struct{}) *sync.WaitGroup

	// WatchDirectoryWithDefaults watches a directory for file changes with default 500ms polling interval
	WatchDirectoryWithDefaults(path string, callback func([]*filesystem.FileChangeEvent), stopCh <-chan struct{}) *sync.WaitGroup
}
