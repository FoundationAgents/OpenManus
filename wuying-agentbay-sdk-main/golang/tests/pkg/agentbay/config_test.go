package agentbay_test

import (
	"fmt"
	"os"
	"path"
	"testing"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
	"github.com/stretchr/testify/assert"
)

func TestLoadConfig_WithExplicitConfig(t *testing.T) {
	// test whether the LoadConfig function works as expected when a custom config is provided.
	customCfg := &agentbay.Config{
		Endpoint:  "custom-endpoint",
		TimeoutMs: 5000,
	}

	result := agentbay.LoadConfig(customCfg, "")

	assert.Equal(t, "custom-endpoint", result.Endpoint)
	assert.Equal(t, 5000, result.TimeoutMs)
}

func TestLoadConfig_FromEnvFile(t *testing.T) {
	// create temp dir and create .env file
	dir := t.TempDir()
	envFilePath := path.Join(dir, ".env")
	err := os.WriteFile(envFilePath, []byte(`
AGENTBAY_ENDPOINT=env-endpoint
AGENTBAY_TIMEOUT_MS=10000
`), 0644)
	if err != nil {
		t.Fatalf("Failed to create .env file: %v", err)
	}

	// clear environment variables
	os.Unsetenv("AGENTBAY_ENDPOINT")
	os.Unsetenv("AGENTBAY_TIMEOUT_MS")

	// switch to temp dir
	cwd, _ := os.Getwd()
	defer os.Chdir(cwd)
	os.Chdir(dir)

	result := agentbay.LoadConfig(nil, "")

	assert.Equal(t, "env-endpoint", result.Endpoint)
	assert.Equal(t, 10000, result.TimeoutMs)
}

func TestLoadConfig_FromEnvironmentVariables(t *testing.T) {
	// set environment variables
	os.Setenv("AGENTBAY_ENDPOINT", "sys-endpoint")
	os.Setenv("AGENTBAY_TIMEOUT_MS", "15000")
	defer func() {
		os.Unsetenv("AGENTBAY_ENDPOINT")
		os.Unsetenv("AGENTBAY_TIMEOUT_MS")
	}()

	result := agentbay.LoadConfig(nil, "")

	assert.Equal(t, "sys-endpoint", result.Endpoint)
	assert.Equal(t, 15000, result.TimeoutMs)
}

func TestLoadConfig_UsesDefaultsWhenNoSource(t *testing.T) {
	// ensure environment variables are cleared
	os.Unsetenv("AGENTBAY_ENDPOINT")
	os.Unsetenv("AGENTBAY_TIMEOUT_MS")

	result := agentbay.LoadConfig(nil, "")

	defaultCfg := agentbay.DefaultConfig()
	assert.Equal(t, defaultCfg.Endpoint, result.Endpoint)
	assert.Equal(t, defaultCfg.TimeoutMs, result.TimeoutMs)
}

func TestLoadConfig_ConfigPrecedenceOrder(t *testing.T) {
	dir := t.TempDir()
	envFilePath := path.Join(dir, ".env")
	err := os.WriteFile(envFilePath, []byte(fmt.Sprintf(`
AGENTBAY_ENDPOINT=env-endpoint
AGENTBAY_TIMEOUT_MS=10000
`)), 0644)
	if err != nil {
		t.Fatalf("Failed to create .env file: %v", err)
	}

	// change to temp dir
	cwd, _ := os.Getwd()
	defer os.Chdir(cwd)
	os.Chdir(dir)

	// set environment variables
	os.Setenv("AGENTBAY_ENDPOINT", "sys-endpoint")
	os.Setenv("AGENTBAY_TIMEOUT_MS", "15000")
	defer func() {
		os.Unsetenv("AGENTBAY_ENDPOINT")
		os.Unsetenv("AGENTBAY_TIMEOUT_MS")
	}()

	// default config
	defaultCfg := agentbay.DefaultConfig()

	// 1. explicit config should take precedence over env vars
	customCfg := &agentbay.Config{
		Endpoint:  "explicit-endpoint",
		TimeoutMs: 2000,
	}
	result := agentbay.LoadConfig(customCfg, "")
	assert.Equal(t, "explicit-endpoint", result.Endpoint)
	assert.Equal(t, 2000, result.TimeoutMs)

	// 2. when there is no explicit config, env vars should take precedence over default config
	result = agentbay.LoadConfig(nil, "")
	assert.Equal(t, "sys-endpoint", result.Endpoint)
	assert.Equal(t, 15000, result.TimeoutMs)

	// 3. after clearing environment variables, env vars should take precedence over default config
	os.Unsetenv("AGENTBAY_ENDPOINT")
	os.Unsetenv("AGENTBAY_TIMEOUT_MS")

	result = agentbay.LoadConfig(nil, "")
	assert.Equal(t, "env-endpoint", result.Endpoint)
	assert.Equal(t, 10000, result.TimeoutMs)

	// 4. when no env vars are set, default config should be used
	os.Remove(envFilePath)
	os.Unsetenv("AGENTBAY_ENDPOINT")
	os.Unsetenv("AGENTBAY_TIMEOUT_MS")

	result = agentbay.LoadConfig(nil, "")
	assert.Equal(t, defaultCfg.Endpoint, result.Endpoint)
	assert.Equal(t, defaultCfg.TimeoutMs, result.TimeoutMs)
}
