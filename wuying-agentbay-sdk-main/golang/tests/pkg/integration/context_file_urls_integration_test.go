package integration

import (
	"bytes"
	"fmt"
	"io"
	"net/http"
	"os"
	"testing"
	"time"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestContextFileUrlsIntegration(t *testing.T) {
	apiKey := os.Getenv("AGENTBAY_API_KEY")
	if apiKey == "" || os.Getenv("CI") != "" {
		t.Skip("Skipping integration test: No API key available or running in CI")
	}

	ab, err := agentbay.NewAgentBay(apiKey)
	require.NoError(t, err, "Failed to create AgentBay client")

	contextName := fmt.Sprintf("test-file-url-go-%d", time.Now().Unix())
	ctxRes, err := ab.Context.Get(contextName, true)
	require.NoError(t, err, "Failed to create context for file URL test")
	require.NotNil(t, ctxRes.Context, "Context should not be nil")
	ctx := ctxRes.Context
	// logf prints to both testing logs and stdout for terminal visibility
	logf := func(format string, args ...interface{}) {
		t.Logf(format, args...)
		fmt.Printf(format+"\n", args...)
	}
	logf("Created context: %s (ID: %s)", ctx.Name, ctx.ID)

	defer func() {
		if ctx != nil {
			_, err := ab.Context.Delete(ctx)
			if err != nil {
				logf("Warning: Failed to delete context %s: %v", ctx.Name, err)
			} else {
				logf("Deleted context: %s (ID: %s)", ctx.Name, ctx.ID)
			}
		}
	}()

	// 1) Get upload URL
	testPath := "/tmp/integration_upload_test.txt"
	uploadURLRes, err := ab.Context.GetFileUploadUrl(ctx.ID, testPath)
	require.NoError(t, err)
	require.NotEmpty(t, uploadURLRes.RequestID)
	assert.True(t, uploadURLRes.Success, "get_file_upload_url should be successful")
	assert.True(t, len(uploadURLRes.Url) > 0, "URL should be non-empty")
	if uploadURLRes.ExpireTime != nil {
		// just type check through compilation; no runtime assertion needed beyond non-nil
	}
	logf("Upload URL: %.80s... (RequestID: %s)", uploadURLRes.Url, uploadURLRes.RequestID)

	// 2) Upload content using the presigned URL
	uploadContent := []byte(fmt.Sprintf("agentbay integration upload test at %d\n", time.Now().Unix()))
	req, err := http.NewRequest(http.MethodPut, uploadURLRes.Url, bytes.NewReader(uploadContent))
	require.NoError(t, err)
	client := &http.Client{Timeout: 30 * time.Second}
	resp, err := client.Do(req)
	require.NoError(t, err)
	defer resp.Body.Close()
	assert.Contains(t, []int{200, 204}, resp.StatusCode, fmt.Sprintf("Upload failed with status code %d", resp.StatusCode))
	etag := resp.Header.Get("ETag")
	logf("Uploaded %d bytes, status=%d, ETag=%s", len(uploadContent), resp.StatusCode, etag)

	// 3) Get download URL and verify content
	dlURLRes, err := ab.Context.GetFileDownloadUrl(ctx.ID, testPath)
	require.NoError(t, err)
	assert.True(t, dlURLRes.Success, "get_file_download_url should be successful")
	assert.True(t, len(dlURLRes.Url) > 0, "Download URL should be non-empty")
	logf("Download URL: %.80s... (RequestID: %s)", dlURLRes.Url, dlURLRes.RequestID)

	dlResp, err := client.Get(dlURLRes.Url)
	require.NoError(t, err)
	defer dlResp.Body.Close()
	require.Equal(t, 200, dlResp.StatusCode, fmt.Sprintf("Download failed with status code %d", dlResp.StatusCode))
	dlBytes, err := io.ReadAll(dlResp.Body)
	require.NoError(t, err)
	assert.Equal(t, uploadContent, dlBytes, "Downloaded content does not match uploaded content")
	logf("Downloaded %d bytes, content matches uploaded data", len(dlBytes))

	// 4) List files to verify presence of the uploaded file under /tmp (with small retry)
	fileName := "integration_upload_test.txt"

	listContains := func() (bool, *agentbay.ContextFileListResult, string) {
		res, err := ab.Context.ListFiles(ctx.ID, "/tmp", 1, 50)
		if err != nil || res == nil || !res.Success {
			return false, res, "/tmp"
		}
		found := false
		for _, e := range res.Entries {
			if e == nil {
				continue
			}
			if e.FilePath == testPath || e.FileName == fileName {
				found = true
				break
			}
		}
		if found || len(res.Entries) > 0 {
			return found, res, "/tmp"
		}
		return false, res, "/tmp"
	}

	var (
		present      bool
		lastListRes  *agentbay.ContextFileListResult
		chosenParent string
	)
	retriesPresence := 0
	for i := 0; i < 30; i++ {
		present, lastListRes, chosenParent = listContains()
		if present {
			break
		}
		retriesPresence++
		time.Sleep(2 * time.Second)
	}
	logf("List files retry attempts (presence check): %d", retriesPresence)

	if lastListRes != nil && chosenParent != "" {
		total := 0
		if lastListRes.Count != nil {
			total = int(*lastListRes.Count)
		} else {
			total = len(lastListRes.Entries)
		}
		logf("List files: checked parent=%s, total=%d, contains=%v", chosenParent, total, present)
	} else {
		logf("%s", "List files: no listing result available")
	}

	if lastListRes != nil && len(lastListRes.Entries) > 0 {
		assert.True(t, present, "Uploaded file should appear in list_files")
	}

	// 5) Delete the file and verify it disappears from listing (with small retry)
	delRes, err := ab.Context.DeleteFile(ctx.ID, testPath)
	require.NoError(t, err)
	assert.True(t, delRes.Success, "delete_file should be successful")
	logf("Deleted file: %s", testPath)

	removed := false
	retriesDeletion := 0
	for i := 0; i < 20; i++ {
		p, _, _ := listContains()
		if lastListRes != nil && len(lastListRes.Entries) > 0 {
			if !p {
				removed = true
				break
			}
			removed = false
		} else {
			removed = true
			break
		}
		retriesDeletion++
		time.Sleep(1 * time.Second)
	}
	logf("List files retry attempts (deletion check): %d", retriesDeletion)
	require.True(t, removed, "Deleted file should not appear in list_files when listing is available")
	if lastListRes != nil {
		var prev int
		if lastListRes.Count != nil {
			prev = int(*lastListRes.Count)
		} else {
			prev = len(lastListRes.Entries)
		}
		logf("List files: %s absent after delete (listing availability: %d)", fileName, prev)
	}

	// 6) Attempt to download after delete and log the status (informational)
	postDL, err := ab.Context.GetFileDownloadUrl(ctx.ID, testPath)
	if err == nil && postDL != nil && postDL.Success && len(postDL.Url) > 0 {
		postResp, err := client.Get(postDL.Url)
		if err == nil {
			logf("Post-delete download status (informational): %d", postResp.StatusCode)
			_ = postResp.Body.Close()
		} else {
			logf("%s", "Post-delete: download request failed (informational)")
		}
	} else {
		logf("%s", "Post-delete: download URL not available, treated as deleted")
	}
}
