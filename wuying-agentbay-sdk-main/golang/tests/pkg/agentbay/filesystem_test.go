package agentbay_test

import (
	"fmt"
	"strings"
	"testing"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
	"github.com/aliyun/wuying-agentbay-sdk/golang/tests/pkg/agentbay/testutil"
)

// TestPathPrefix is the prefix for all test file paths
// Change this to "C:" for Windows or "/tmp" for Linux
const TestPathPrefix = "/tmp"

func TestFileSystem_ReadFile(t *testing.T) {
	// Setup session with cleanup and ImageId set to linux_latest
	sessionParams := agentbay.NewCreateSessionParams().WithImageId("linux_latest")
	session, cleanup := testutil.SetupAndCleanup(t, sessionParams)
	defer cleanup()

	// Test FileSystem read operations
	if session.FileSystem != nil {
		// Create a test file with known content
		fmt.Println("Creating a test file for reading...")
		testContent := "This is a test file content for ReadFile test."
		testFilePath := TestPathPrefix + "/test_read.txt"
		writeResult, err := session.FileSystem.WriteFile(testFilePath, testContent, "overwrite")
		if err != nil {
			t.Fatalf("Failed to create test file for reading: %v", err)
		}
		t.Logf("Test file created successfully with RequestID: %s", writeResult.RequestID)

		// Now read the file
		fmt.Println("Reading file...")
		result, err := session.FileSystem.ReadFile(testFilePath)
		if err != nil {
			t.Errorf("File read failed: %v", err)
			return
		}

		t.Logf("ReadFile result: content length=%d, RequestID=%s",
			len(result.Content), result.RequestID)

		if result.Content == "" {
			t.Errorf("Failed to read file content")
			return
		}

		t.Logf("File read successful, content length: %d bytes", len(result.Content))

		// Verify the content matches what was written
		if result.Content != testContent {
			t.Errorf("File content mismatch. Expected: %s, Got: %s", testContent, result.Content)
		} else {
			t.Log("File content verified successfully")
		}

		// Check if response contains "tool not found"
		if testutil.ContainsToolNotFound(result.Content) {
			t.Errorf("FileSystem.ReadFile returned 'tool not found'")
		}

		if result.RequestID == "" {
			t.Errorf("ReadFile method did not return RequestID")
		}
	} else {
		t.Logf("Note: FileSystem interface is nil, skipping file test")
	}
}

func TestFileSystem_WriteFile(t *testing.T) {
	// Setup session with cleanup and ImageId set to linux_latest
	sessionParams := agentbay.NewCreateSessionParams().WithImageId("linux_latest")
	session, cleanup := testutil.SetupAndCleanup(t, sessionParams)
	defer cleanup()

	// Test FileSystem write operations
	if session.FileSystem != nil {
		fmt.Println("Writing file...")
		testContent := "This is a test file content for WriteFile test."
		testFilePath := TestPathPrefix + "/test_write.txt"
		writeResult, err := session.FileSystem.WriteFile(testFilePath, testContent, "overwrite")
		if err != nil {
			t.Errorf("File write failed: %v", err)
			return
		}

		t.Logf("WriteFile result: success=%v, RequestID=%s", writeResult.Success, writeResult.RequestID)
		t.Log("File write successful")

		// Verify the file was written correctly by reading it back
		readResult, err := session.FileSystem.ReadFile(testFilePath)
		if err != nil {
			t.Errorf("Failed to read back written file: %v", err)
			return
		}

		if readResult.Content == "" {
			t.Errorf("Failed to read file content")
			return
		}

		if readResult.Content != testContent {
			t.Errorf("File content mismatch. Expected: %s, Got: %s", testContent, readResult.Content)
		} else {
			t.Log("File content verified successfully")
		}

		if writeResult.RequestID == "" {
			t.Errorf("WriteFile method did not return RequestID")
		}
	} else {
		t.Logf("Note: FileSystem interface is nil, skipping file test")
	}
}

func TestFileSystem_CreateDirectory(t *testing.T) {
	// Setup session with cleanup and ImageId set to linux_latest
	sessionParams := agentbay.NewCreateSessionParams().WithImageId("linux_latest")
	session, cleanup := testutil.SetupAndCleanup(t, sessionParams)
	defer cleanup()

	// Test FileSystem create directory
	if session.FileSystem != nil {
		fmt.Println("Creating directory...")
		dirPath := TestPathPrefix + "/test_directory"
		result, err := session.FileSystem.CreateDirectory(dirPath)
		t.Logf("CreateDirectory result: success=%v, requestID=%s, err=%v",
			result.Success, result.RequestID, err)

		if err != nil {
			t.Errorf("Directory creation failed: %v", err)
		} else if !result.Success {
			t.Errorf("Directory creation returned false")
		} else {
			t.Log("Directory creation successful")

			// Verify RequestID exists
			if result.RequestID == "" {
				t.Logf("Warning: Empty RequestID returned from CreateDirectory")
			}

			// Verify the directory was created by listing the parent directory
			listResult, err := session.FileSystem.ListDirectory(TestPathPrefix + "/")
			if err != nil {
				t.Errorf("Failed to list directory: %v", err)
			} else {
				// Print the count of entries for debugging
				t.Logf("ListDirectory result: entries count=%d, requestID=%s, err=%v",
					len(listResult.Entries), listResult.RequestID, err)

				// Verify RequestID exists for list operation
				if listResult.RequestID == "" {
					t.Logf("Warning: Empty RequestID returned from ListDirectory")
				}

				directoryFound := false
				for _, entry := range listResult.Entries {
					if entry.IsDirectory && entry.Name == "test_directory" {
						directoryFound = true
						break
					}
				}
				if !directoryFound {
					t.Errorf("Created directory not found in listing")
				} else {
					t.Log("Directory verified in listing")
				}
			}
		}

		if result.RequestID == "" {
			t.Errorf("CreateDirectory method did not return RequestID")
		}
	} else {
		t.Logf("Note: FileSystem interface is nil, skipping directory test")
	}
}

func TestFileSystem_EditFile(t *testing.T) {
	// Setup session with cleanup and ImageId set to linux_latest
	sessionParams := agentbay.NewCreateSessionParams().WithImageId("linux_latest")
	session, cleanup := testutil.SetupAndCleanup(t, sessionParams)
	defer cleanup()

	// Test FileSystem edit operations
	if session.FileSystem != nil {
		// First create a file to edit
		initialContent := "This is the original content.\nLine to be replaced.\nThis is the final line."
		testFilePath := TestPathPrefix + "/test_edit.txt"
		writeResult, err := session.FileSystem.WriteFile(testFilePath, initialContent, "overwrite")
		if err != nil {
			t.Fatalf("Failed to create file for editing: %v", err)
		}
		t.Logf("Test file created with RequestID: %s", writeResult.RequestID)

		// Now edit the file
		fmt.Println("Editing file...")
		edits := []map[string]string{
			{
				"oldText": "Line to be replaced.",
				"newText": "This line has been edited.",
			},
		}
		editResult, err := session.FileSystem.EditFile(testFilePath, edits, false)
		if err != nil {
			t.Errorf("File edit failed: %v", err)
			return
		}

		t.Logf("EditFile result: success=%v, RequestID=%s", editResult.Success, editResult.RequestID)
		t.Log("File edit successful")

		// Verify the file was edited correctly by reading it back
		readResult, err := session.FileSystem.ReadFile(testFilePath)
		if err != nil {
			t.Errorf("Failed to read back edited file: %v", err)
			return
		}

		if readResult.Content == "" {
			t.Errorf("Failed to read file content")
			return
		}

		expectedContent := "This is the original content.\nThis line has been edited.\nThis is the final line."
		if readResult.Content != expectedContent {
			t.Errorf("File content mismatch after edit. Expected: %s, Got: %s", expectedContent, readResult.Content)
		} else {
			t.Log("File edit verified successfully")
		}

		if editResult.RequestID == "" {
			t.Errorf("EditFile method did not return RequestID")
		}
	} else {
		t.Logf("Note: FileSystem interface is nil, skipping file edit test")
	}
}

func TestFileSystem_GetFileInfo(t *testing.T) {
	// Setup session with cleanup and ImageId set to linux_latest
	sessionParams := agentbay.NewCreateSessionParams().WithImageId("linux_latest")
	session, cleanup := testutil.SetupAndCleanup(t, sessionParams)
	defer cleanup()

	// Test FileSystem get file info
	if session.FileSystem != nil {
		// First create a file to get info about
		testContent := "This is a test file content for GetFileInfo test."
		testFilePath := TestPathPrefix + "/test_fileinfo.txt"
		writeResult, err := session.FileSystem.WriteFile(testFilePath, testContent, "overwrite")
		if err != nil {
			t.Fatalf("Failed to create test file for GetFileInfo: %v", err)
		}
		t.Logf("Test file created with RequestID: %s", writeResult.RequestID)

		// Get file info
		fmt.Println("Getting file info...")
		fileInfoResult, err := session.FileSystem.GetFileInfo(testFilePath)
		if err != nil {
			t.Errorf("GetFileInfo failed: %v", err)
		} else {
			t.Log("GetFileInfo successful")
			t.Logf("FileInfo result: size=%d, isDirectory=%v, RequestID=%s, err=%v",
				fileInfoResult.FileInfo.Size, fileInfoResult.FileInfo.IsDirectory, fileInfoResult.RequestID, err)

			// Verify the file info
			if fileInfoResult.FileInfo.Size <= 0 {
				t.Errorf("Expected positive file size, got %d", fileInfoResult.FileInfo.Size)
			}
			if fileInfoResult.FileInfo.IsDirectory {
				t.Errorf("Expected file to not be a directory")
			}
			// Don't check for Name since it's not returned by the server
		}

		// Verify RequestID exists (only if we got a result)
		if fileInfoResult != nil && fileInfoResult.RequestID == "" {
			t.Errorf("GetFileInfo method did not return RequestID")
		}
	} else {
		t.Logf("Note: FileSystem interface is nil, skipping file info test")
	}
}

func TestFileSystem_ListDirectory(t *testing.T) {
	// Setup session with cleanup and ImageId set to linux_latest
	sessionParams := agentbay.NewCreateSessionParams().WithImageId("linux_latest")
	session, cleanup := testutil.SetupAndCleanup(t, sessionParams)
	defer cleanup()

	// Prepare a test directory with some files
	dirPath := TestPathPrefix + "/test_list_dir"
	createResult, err := session.FileSystem.CreateDirectory(dirPath)
	if err != nil {
		t.Fatalf("Failed to create test directory: %v", err)
	}
	t.Logf("Test directory created with RequestID: %s", createResult.RequestID)

	// Create a few test files in the directory
	_, err = session.FileSystem.WriteFile(dirPath+"/file1.txt", "File 1 content", "overwrite")
	if err != nil {
		t.Fatalf("Failed to create test file 1: %v", err)
	}
	_, err = session.FileSystem.WriteFile(dirPath+"/file2.txt", "File 2 content", "overwrite")
	if err != nil {
		t.Fatalf("Failed to create test file 2: %v", err)
	}

	// Create a subdirectory
	subDirResult, err := session.FileSystem.CreateDirectory(dirPath + "/subdir")
	if err != nil {
		t.Fatalf("Failed to create subdirectory: %v", err)
	}
	t.Logf("Subdirectory created with RequestID: %s", subDirResult.RequestID)

	// Test listing the directory
	fmt.Println("Listing directory...")
	listResult, err := session.FileSystem.ListDirectory(dirPath)
	if err != nil {
		t.Errorf("Failed to list directory: %v", err)
		return
	}

	// Verify RequestID exists
	if listResult.RequestID == "" {
		t.Logf("Warning: Empty RequestID returned from ListDirectory")
	}

	t.Logf("Directory listing successful, found %d entries", len(listResult.Entries))

	// Verify the expected files and directory are in the listing
	expectedEntries := map[string]bool{
		"file1.txt": false,
		"file2.txt": false,
		"subdir":    true,
	}

	for _, entry := range listResult.Entries {
		isDir, exists := expectedEntries[entry.Name]
		if exists {
			if isDir != entry.IsDirectory {
				t.Errorf("Entry %s: expected isDirectory=%v, got %v", entry.Name, isDir, entry.IsDirectory)
			} else {
				delete(expectedEntries, entry.Name)
			}
		}
	}

	if len(expectedEntries) > 0 {
		var missing []string
		for name := range expectedEntries {
			missing = append(missing, name)
		}
		t.Errorf("Some expected entries were not found: %v", missing)
	}

	if listResult.RequestID == "" {
		t.Errorf("ListDirectory method did not return RequestID")
	}
}

func TestFileSystem_MoveFile(t *testing.T) {
	// Setup session with cleanup and ImageId set to linux_latest
	sessionParams := agentbay.NewCreateSessionParams().WithImageId("linux_latest")
	session, cleanup := testutil.SetupAndCleanup(t, sessionParams)
	defer cleanup()

	// Test FileSystem move file
	if session.FileSystem != nil {
		// First create a file to move
		initialContent := "This is a test file content for MoveFile test."
		srcFilePath := TestPathPrefix + "/test_move_source.txt"
		destFilePath := TestPathPrefix + "/test_move_dest.txt"

		// Create the source file
		writeResult, err := session.FileSystem.WriteFile(srcFilePath, initialContent, "overwrite")
		if err != nil {
			t.Fatalf("Failed to create test file for moving: %v", err)
		}
		t.Logf("Test file created successfully with RequestID: %s", writeResult.RequestID)

		// Move the file
		fmt.Println("Moving file...")
		moveResult, err := session.FileSystem.MoveFile(srcFilePath, destFilePath)
		t.Logf("MoveFile result: success=%v, requestID=%s, err=%v",
			moveResult.Success, moveResult.RequestID, err)

		if err != nil {
			t.Errorf("File move failed: %v", err)
		} else {
			t.Log("File move successful")

			// Verify RequestID exists
			if moveResult.RequestID == "" {
				t.Logf("Warning: Empty RequestID returned from MoveFile")
			}

			// Verify the source file doesn't exist anymore
			_, err = session.FileSystem.GetFileInfo(srcFilePath)
			if err == nil {
				t.Errorf("Source file still exists after move")
			}

			// Verify the destination file exists and has the correct content
			readResult, err := session.FileSystem.ReadFile(destFilePath)
			if err != nil {
				t.Errorf("Failed to read destination file: %v", err)
				return
			}

			if readResult.Content == "" {
				t.Errorf("Failed to read destination file content")
				return
			}

			// Verify the content matches what was written
			if readResult.Content != initialContent {
				t.Errorf("Destination file content mismatch. Expected: %s, Got: %s",
					initialContent, readResult.Content)
			} else {
				t.Log("File content verified successfully after move")
			}
		}

		if moveResult.RequestID == "" {
			t.Errorf("MoveFile method did not return RequestID")
		}
	} else {
		t.Logf("Note: FileSystem interface is nil, skipping file move test")
	}
}

func TestFileSystem_ReadMultipleFiles(t *testing.T) {
	// Setup session with cleanup and ImageId set to linux_latest
	sessionParams := agentbay.NewCreateSessionParams().WithImageId("linux_latest")
	session, cleanup := testutil.SetupAndCleanup(t, sessionParams)
	defer cleanup()

	// Test FileSystem read multiple files
	if session.FileSystem != nil {
		// First create some test files
		file1Content := "This is test file 1 content."
		file2Content := "This is test file 2 content."
		testFile1Path := TestPathPrefix + "/test_file1.txt"
		_, err := session.FileSystem.WriteFile(testFile1Path, file1Content, "overwrite")
		if err != nil {
			t.Fatalf("Failed to create test file 1: %v", err)
		}
		testFile2Path := TestPathPrefix + "/test_file2.txt"
		_, err = session.FileSystem.WriteFile(testFile2Path, file2Content, "overwrite")
		if err != nil {
			t.Fatalf("Failed to create test file 2: %v", err)
		}

		fmt.Println("Reading multiple files...")
		paths := []string{testFile1Path, testFile2Path}
		contents, err := session.FileSystem.ReadMultipleFiles(paths)
		if err != nil {
			t.Errorf("Read multiple files failed: %v", err)
		} else {
			t.Log("Read multiple files successful")

			t.Logf("ReadMultipleFiles result: contents count=%d, err=%v", len(contents), err)

			// Verify the contents of each file
			if content, ok := contents[testFile1Path]; !ok {
				t.Errorf("File 1 content missing")
			} else {
				// Trim trailing newline if present
				trimmedContent := strings.TrimSuffix(content, "\n")
				if trimmedContent != file1Content {
					t.Errorf("File 1 content mismatch. Expected: %q (len=%d), Got: %q (len=%d)",
						file1Content, len(file1Content), trimmedContent, len(trimmedContent))
					// Print byte by byte comparison for debugging
					t.Logf("Expected bytes: %v", []byte(file1Content))
					t.Logf("Actual bytes: %v", []byte(trimmedContent))
				} else {
					t.Log("File 1 content verified successfully")
				}
			}

			if content, ok := contents[testFile2Path]; !ok {
				t.Errorf("File 2 content missing")
			} else {
				// Trim trailing newline if present
				trimmedContent := strings.TrimSuffix(content, "\n")
				if trimmedContent != file2Content {
					t.Errorf("File 2 content mismatch. Expected: %q (len=%d), Got: %q (len=%d)",
						file2Content, len(file2Content), trimmedContent, len(trimmedContent))
				} else {
					t.Log("File 2 content verified successfully")
				}
			}
		}
	} else {
		t.Logf("Note: FileSystem interface is nil, skipping multiple files test")
	}
}

func TestFileSystem_SearchFiles(t *testing.T) {
	// Setup session with cleanup and ImageId set to linux_latest
	sessionParams := agentbay.NewCreateSessionParams().WithImageId("linux_latest")
	session, cleanup := testutil.SetupAndCleanup(t, sessionParams)
	defer cleanup()

	// Test FileSystem search files
	if session.FileSystem != nil {
		// First create a subdirectory for testing
		testSubdirPath := TestPathPrefix + "/search_test_dir"
		fmt.Println("Creating a subdirectory for search testing...")
		dirResult, err := session.FileSystem.CreateDirectory(testSubdirPath)
		if err != nil {
			t.Fatalf("Failed to create test subdirectory: %v", err)
		}
		if !dirResult.Success {
			t.Fatalf("Failed to create test subdirectory: operation returned false")
		}
		t.Logf("Test subdirectory created successfully (RequestID: %s)", dirResult.RequestID)

		// Create test files with specific naming patterns
		file1Content := "This is test file 1 content."
		file2Content := "This is test file 2 content."
		file3Content := "This is test file 3 content."

		// Note: The pattern to search for is in the file names, not the content
		searchFile1Path := testSubdirPath + "/SEARCHABLE_PATTERN_file1.txt"
		writeResult1, err := session.FileSystem.WriteFile(searchFile1Path, file1Content, "overwrite")
		if err != nil {
			t.Fatalf("Failed to create search test file 1: %v", err)
		}
		t.Logf("Search test file 1 created (RequestID: %s)", writeResult1.RequestID)

		searchFile2Path := testSubdirPath + "/regular_file2.txt"
		writeResult2, err := session.FileSystem.WriteFile(searchFile2Path, file2Content, "overwrite")
		if err != nil {
			t.Fatalf("Failed to create search test file 2: %v", err)
		}
		t.Logf("Search test file 2 created (RequestID: %s)", writeResult2.RequestID)

		searchFile3Path := testSubdirPath + "/SEARCHABLE_PATTERN_file3.txt"
		writeResult3, err := session.FileSystem.WriteFile(searchFile3Path, file3Content, "overwrite")
		if err != nil {
			t.Fatalf("Failed to create search test file 3: %v", err)
		}
		t.Logf("Search test file 3 created (RequestID: %s)", writeResult3.RequestID)

		fmt.Println("Searching files in subdirectory...")
		// Search for files with names containing the pattern
		searchPattern := "SEARCHABLE_PATTERN"
		excludePatterns := []string{"ignored_pattern"}
		searchResults, err := session.FileSystem.SearchFiles(testSubdirPath, searchPattern, excludePatterns)
		if err != nil {
			t.Errorf("Search files failed: %v", err)
		} else {
			t.Log("Search files successful")
			t.Logf("SearchFiles result: found %d files, RequestID=%s, err=%v", len(searchResults.Results), searchResults.RequestID, err)

			// Extract search results
			var results []map[string]string

			// Check if no matches were found
			if len(searchResults.Results) == 0 {
				t.Logf("No matches found in search results")
			} else {
				// Process each result path
				for _, path := range searchResults.Results {
					path = strings.TrimSpace(path)
					if path == "" {
						continue
					}

					// Create a result entry for each file path
					resultMap := map[string]string{
						"path": path,
					}
					results = append(results, resultMap)
				}
			}

			// Verify we found the expected number of results (should be 2 files)
			if len(results) != 2 {
				t.Errorf("Unexpected number of search results. Expected: 2, Got: %d", len(results))
			} else {
				t.Log("Search found the expected number of results")
			}

			// Verify the search results contain the expected files
			foundFile1 := false
			foundFile3 := false

			for _, result := range results {
				path := result["path"]

				// Normalize paths for comparison (replace backslashes with forward slashes)
				normalizedPath := path
				normalizedPath = strings.ReplaceAll(normalizedPath, "\\", "/")

				// Log the paths for debugging
				t.Logf("Comparing result path: %s with expected paths: %s and %s",
					normalizedPath, searchFile1Path, searchFile3Path)

				if normalizedPath == searchFile1Path {
					foundFile1 = true
				} else if normalizedPath == searchFile3Path {
					foundFile3 = true
				}
			}

			if !foundFile1 {
				t.Errorf("Search results missing file 1")
			}
			if !foundFile3 {
				t.Errorf("Search results missing file 3")
			}

			if foundFile1 && foundFile3 {
				t.Log("Search results contain the expected files")
			}
		}
		// Verify RequestID exists
		if searchResults != nil && searchResults.RequestID == "" {
			t.Errorf("SearchFiles method did not return RequestID")
		}
	} else {
		t.Logf("Note: FileSystem interface is nil, skipping search files test")
	}
}

func TestFileSystem_LargeFileOperations(t *testing.T) {
	// Setup session with cleanup and ImageId set to linux_latest
	sessionParams := agentbay.NewCreateSessionParams().WithImageId("linux_latest")
	session, cleanup := testutil.SetupAndCleanup(t, sessionParams)
	defer cleanup()

	// Test FileSystem large file operations
	if session.FileSystem != nil {
		// Generate a large string (approximately 150KB)
		var largeContent strings.Builder
		lineContent := "This is a line of test content for large file testing. It contains enough characters to test the chunking functionality.\n"

		// Generate about 150KB of data (60KB is the default chunk size)
		targetSize := 150 * 1024 // 150KB
		for largeContent.Len() < targetSize {
			largeContent.WriteString(lineContent)
		}

		testContent := largeContent.String()
		t.Logf("Generated test content of size: %d bytes", len(testContent))

		// Test 1: Write large file (automatic chunking)
		testFilePath1 := TestPathPrefix + "/test_large_file1.txt"
		fmt.Println("Test 1: Writing large file with automatic chunking...")
		writeResult1, err := session.FileSystem.WriteFile(testFilePath1, testContent, "overwrite")
		if err != nil {
			t.Fatalf("WriteFile failed for large file: %v", err)
		}
		if !writeResult1.Success {
			t.Errorf("WriteFile returned false for large file")
		} else {
			t.Logf("Test 1: Large file write successful with automatic chunking (RequestID: %s)",
				writeResult1.RequestID)
		}

		// Test 2: Read the large file (automatic chunking)
		fmt.Println("Test 2: Reading large file with automatic chunking...")
		readResult1, err := session.FileSystem.ReadFile(testFilePath1)
		if err != nil {
			t.Fatalf("ReadFile failed for large file: %v", err)
		}

		// Verify content
		t.Logf("Test 2: File read successful, content length: %d bytes (RequestID: %s)",
			len(readResult1.Content), readResult1.RequestID)

		if readResult1.Content != testContent {
			t.Errorf("File content mismatch for large file. Expected length: %d, Got length: %d",
				len(testContent), len(readResult1.Content))

			// Find first mismatch position
			minLen := len(testContent)
			if len(readResult1.Content) < minLen {
				minLen = len(readResult1.Content)
			}

			for i := 0; i < minLen; i++ {
				if testContent[i] != readResult1.Content[i] {
					t.Errorf("First mismatch at position %d: expected '%c', got '%c'",
						i, testContent[i], readResult1.Content[i])
					break
				}
			}
		} else {
			t.Log("Test 2: File content verified successfully for large file")
		}

		// Test 3: Write another large file
		testFilePath2 := TestPathPrefix + "/test_large_file2.txt"
		fmt.Println("Test 3: Writing another large file...")

		writeResult2, err := session.FileSystem.WriteFile(testFilePath2, testContent, "overwrite")
		if err != nil {
			t.Fatalf("WriteFile failed for second large file: %v", err)
		}
		if !writeResult2.Success {
			t.Errorf("WriteFile returned false for second large file")
		} else {
			t.Logf("Test 3: Second large file write successful (RequestID: %s)",
				writeResult2.RequestID)
		}

		// Test 4: Read the second large file
		fmt.Println("Test 4: Reading the second large file...")
		readResult2, err := session.FileSystem.ReadFile(testFilePath2)
		if err != nil {
			t.Fatalf("ReadFile failed for second large file: %v", err)
		}

		// Verify content
		t.Logf("Test 4: Second file read successful, content length: %d bytes (RequestID: %s)",
			len(readResult2.Content), readResult2.RequestID)

		if readResult2.Content != testContent {
			t.Errorf("File content mismatch for second large file. Expected length: %d, Got length: %d",
				len(testContent), len(readResult2.Content))
		} else {
			t.Log("Test 4: Second file content verified successfully")
		}

		// Verify RequestID for the last operation
		if writeResult2.RequestID == "" {
			t.Errorf("WriteLargeFile method did not return RequestID")
		}
	} else {
		t.Logf("Note: FileSystem interface is nil, skipping large file operations test")
	}
}
