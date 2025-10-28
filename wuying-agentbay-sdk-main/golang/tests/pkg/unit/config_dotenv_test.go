package agentbay_test

import (
	"io/ioutil"
	"os"
	"path/filepath"
	"testing"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
	"github.com/stretchr/testify/assert"
)

func TestEnhancedDotEnvLoading(t *testing.T) {
	// Save original environment
	originalEnv := make(map[string]string)
	envVars := []string{"AGENTBAY_ENDPOINT", "AGENTBAY_TIMEOUT_MS"}
	for _, key := range envVars {
		if val, exists := os.LookupEnv(key); exists {
			originalEnv[key] = val
		}
		os.Unsetenv(key)
	}

	// Restore environment after tests
	defer func() {
		for _, key := range envVars {
			os.Unsetenv(key)
		}
		for key, val := range originalEnv {
			os.Setenv(key, val)
		}
	}()

	t.Run("FindDotEnvFile_CurrentDirectory", func(t *testing.T) {
		// Create temporary directory
		tmpDir, err := ioutil.TempDir("", "agentbay-test-")
		assert.NoError(t, err)
		defer os.RemoveAll(tmpDir)

		// Create .env file
		envFile := filepath.Join(tmpDir, ".env")
		err = ioutil.WriteFile(envFile, []byte("TEST_VAR=current_dir"), 0644)
		assert.NoError(t, err)

		// Find .env file
		foundFile := agentbay.FindDotEnvFile(tmpDir)
		assert.Equal(t, envFile, foundFile)

		// Verify file exists
		_, err = os.Stat(foundFile)
		assert.NoError(t, err)
	})

	t.Run("FindDotEnvFile_ParentDirectory", func(t *testing.T) {
		// Create temporary directory structure
		tmpDir, err := ioutil.TempDir("", "agentbay-test-")
		assert.NoError(t, err)
		defer os.RemoveAll(tmpDir)

		// Create .env in parent directory
		parentEnv := filepath.Join(tmpDir, ".env")
		err = ioutil.WriteFile(parentEnv, []byte("TEST_VAR=parent_dir"), 0644)
		assert.NoError(t, err)

		// Create subdirectory
		subDir := filepath.Join(tmpDir, "subdir")
		err = os.Mkdir(subDir, 0755)
		assert.NoError(t, err)

		// Find .env file from subdirectory
		foundFile := agentbay.FindDotEnvFile(subDir)
		assert.Equal(t, parentEnv, foundFile)
	})

	t.Run("FindDotEnvFile_GitRepoRoot", func(t *testing.T) {
		// Create temporary directory structure
		tmpDir, err := ioutil.TempDir("", "agentbay-test-")
		assert.NoError(t, err)
		defer os.RemoveAll(tmpDir)

		// Create .git directory (simulate git repo)
		gitDir := filepath.Join(tmpDir, ".git")
		err = os.Mkdir(gitDir, 0755)
		assert.NoError(t, err)

		// Create .env in git root
		gitEnv := filepath.Join(tmpDir, ".env")
		err = ioutil.WriteFile(gitEnv, []byte("TEST_VAR=git_root"), 0644)
		assert.NoError(t, err)

		// Create nested subdirectory
		deepDir := filepath.Join(tmpDir, "src", "deep")
		err = os.MkdirAll(deepDir, 0755)
		assert.NoError(t, err)

		// Find .env file from deep subdirectory
		foundFile := agentbay.FindDotEnvFile(deepDir)
		assert.Equal(t, gitEnv, foundFile)
	})

	t.Run("FindDotEnvFile_NotFound", func(t *testing.T) {
		// Create temporary directory without .env
		tmpDir, err := ioutil.TempDir("", "agentbay-test-")
		assert.NoError(t, err)
		defer os.RemoveAll(tmpDir)

		subDir := filepath.Join(tmpDir, "subdir")
		err = os.Mkdir(subDir, 0755)
		assert.NoError(t, err)

		// No .env file anywhere
		foundFile := agentbay.FindDotEnvFile(subDir)
		assert.Equal(t, "", foundFile)
	})

	t.Run("LoadDotEnvWithFallback_CustomPath", func(t *testing.T) {
		// Create temporary directory
		tmpDir, err := ioutil.TempDir("", "agentbay-test-")
		assert.NoError(t, err)
		defer os.RemoveAll(tmpDir)

		// Create custom .env file
		customEnv := filepath.Join(tmpDir, "custom.env")
		err = ioutil.WriteFile(customEnv, []byte("CUSTOM_VAR=custom_value"), 0644)
		assert.NoError(t, err)

		// Clear any existing env var
		os.Unsetenv("CUSTOM_VAR")

		// Load custom .env file
		agentbay.LoadDotEnvWithFallback(customEnv)

		// Check if variable was loaded
		assert.Equal(t, "custom_value", os.Getenv("CUSTOM_VAR"))

		// Cleanup
		os.Unsetenv("CUSTOM_VAR")
	})

	t.Run("LoadConfig_CustomEnvFile", func(t *testing.T) {
		// Create temporary directory
		tmpDir, err := ioutil.TempDir("", "agentbay-test-")
		assert.NoError(t, err)
		defer os.RemoveAll(tmpDir)

		// Create custom .env file
		customEnv := filepath.Join(tmpDir, "test.env")
		envContent := `AGENTBAY_ENDPOINT=wuyingai.ap-southeast-1.aliyuncs.com
AGENTBAY_TIMEOUT_MS=30000`
		err = ioutil.WriteFile(customEnv, []byte(envContent), 0644)
		assert.NoError(t, err)

		// Load config with custom .env file
		config := agentbay.LoadConfig(nil, customEnv)

		// Check if config was loaded from custom .env file
		assert.Equal(t, "wuyingai.ap-southeast-1.aliyuncs.com", config.Endpoint)
		assert.Equal(t, 30000, config.TimeoutMs)
	})

	t.Run("LoadConfig_UpwardSearch", func(t *testing.T) {
		// Save and clear environment variables to ensure .env file is used
		originalEndpoint := os.Getenv("AGENTBAY_ENDPOINT")
		os.Unsetenv("AGENTBAY_ENDPOINT")
		defer func() {
			if originalEndpoint != "" {
				os.Setenv("AGENTBAY_ENDPOINT", originalEndpoint)
			}
		}()

		// Create temporary directory structure
		tmpDir, err := ioutil.TempDir("", "agentbay-test-")
		assert.NoError(t, err)
		defer os.RemoveAll(tmpDir)

		// Create .env in parent
		parentEnv := filepath.Join(tmpDir, ".env")
		err = ioutil.WriteFile(parentEnv, []byte("AGENTBAY_ENDPOINT=wuyingai.cn-shanghai.aliyuncs.com"), 0644)
		assert.NoError(t, err)

		// Create subdirectory
		subDir := filepath.Join(tmpDir, "project", "src")
		err = os.MkdirAll(subDir, 0755)
		assert.NoError(t, err)

		// Save current working directory
		originalWd, err := os.Getwd()
		assert.NoError(t, err)

		// Change to subdirectory
		err = os.Chdir(subDir)
		assert.NoError(t, err)

		// Restore working directory after test
		defer func() {
			os.Chdir(originalWd)
		}()

		// Load config (should find .env from parent)
		config := agentbay.LoadConfig(nil, "")

		// Should find .env from parent directory
		assert.Equal(t, "wuyingai.cn-shanghai.aliyuncs.com", config.Endpoint)
	})

	t.Run("EnvironmentVariablePrecedence", func(t *testing.T) {
		// Create temporary directory
		tmpDir, err := ioutil.TempDir("", "agentbay-test-")
		assert.NoError(t, err)
		defer os.RemoveAll(tmpDir)

		// Create .env file
		envFile := filepath.Join(tmpDir, ".env")
		err = ioutil.WriteFile(envFile, []byte("AGENTBAY_ENDPOINT=wuyingai.from-env-file.aliyuncs.com"), 0644)
		assert.NoError(t, err)

		// Set environment variable (higher precedence)
		os.Setenv("AGENTBAY_ENDPOINT", "wuyingai.from-environment.aliyuncs.com")

		// Load config
		config := agentbay.LoadConfig(nil, envFile)

		// Environment variable should take precedence
		assert.Equal(t, "wuyingai.from-environment.aliyuncs.com", config.Endpoint)

		// Cleanup
		os.Unsetenv("AGENTBAY_ENDPOINT")
	})

	t.Run("InvalidTimeoutHandling", func(t *testing.T) {
		// Save and clear environment variables to ensure clean state
		originalTimeout := os.Getenv("AGENTBAY_TIMEOUT_MS")
		os.Unsetenv("AGENTBAY_TIMEOUT_MS")
		defer func() {
			if originalTimeout != "" {
				os.Setenv("AGENTBAY_TIMEOUT_MS", originalTimeout)
			}
		}()

		// Create temporary directory
		tmpDir, err := ioutil.TempDir("", "agentbay-test-")
		assert.NoError(t, err)
		defer os.RemoveAll(tmpDir)

		// Create .env file with invalid timeout
		envFile := filepath.Join(tmpDir, ".env")
		err = ioutil.WriteFile(envFile, []byte("AGENTBAY_TIMEOUT_MS=invalid_number"), 0644)
		assert.NoError(t, err)

		// Load config
		config := agentbay.LoadConfig(nil, envFile)

		// Should use default timeout value
		defaultConfig := agentbay.DefaultConfig()
		assert.Equal(t, defaultConfig.TimeoutMs, config.TimeoutMs)
	})

	t.Run("ConfigPrecedenceOrder", func(t *testing.T) {
		// Create temporary directory
		tmpDir, err := ioutil.TempDir("", "agentbay-test-")
		assert.NoError(t, err)
		defer os.RemoveAll(tmpDir)

		// 1. Custom config (highest priority)
		customConfig := &agentbay.Config{
			Endpoint:  "custom.com",
			TimeoutMs: 1000,
		}

		// 2. Environment variable
		os.Setenv("AGENTBAY_ENDPOINT", "wuyingai.from-env.aliyuncs.com")

		// 3. .env file (lowest priority)
		envFile := filepath.Join(tmpDir, ".env")
		err = ioutil.WriteFile(envFile, []byte("AGENTBAY_ENDPOINT=wuyingai.from-file.aliyuncs.com"), 0644)
		assert.NoError(t, err)

		// Test custom config precedence
		configWithCustom := agentbay.LoadConfig(customConfig, envFile)
		assert.Equal(t, "custom.com", configWithCustom.Endpoint)

		// Test environment variable precedence over .env file
		configWithEnv := agentbay.LoadConfig(nil, envFile)
		assert.Equal(t, "wuyingai.from-env.aliyuncs.com", configWithEnv.Endpoint)

		// Cleanup
		os.Unsetenv("AGENTBAY_ENDPOINT")
	})

	t.Run("BackwardCompatibility", func(t *testing.T) {
		// Test that LoadConfigCompat still works
		customConfig := &agentbay.Config{
			Endpoint:  "compat.com",
			TimeoutMs: 2000,
		}

		config := agentbay.LoadConfigCompat(customConfig)
		assert.Equal(t, "compat.com", config.Endpoint)
		assert.Equal(t, 2000, config.TimeoutMs)
	})

	t.Run("ConfigManager_Interface", func(t *testing.T) {
		// Test ConfigManager interface implementation
		manager := agentbay.NewConfigManager()

		// Test DefaultConfig method
		defaultConfig := manager.DefaultConfig()
		assert.Equal(t, "wuyingai.cn-shanghai.aliyuncs.com", defaultConfig.Endpoint)

		// Test LoadConfig method
		customConfig := &agentbay.Config{
			Endpoint:  "interface.com",
			TimeoutMs: 3000,
		}

		config := manager.LoadConfig(customConfig)
		assert.Equal(t, "interface.com", config.Endpoint)
		assert.Equal(t, 3000, config.TimeoutMs)
	})
}
