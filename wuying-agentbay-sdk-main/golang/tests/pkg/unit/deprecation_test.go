package agentbay_test

import (
	"bytes"
	"fmt"
	"log"
	"os"
	"strings"
	"testing"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/deprecation"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/suite"
)

type DeprecationTestSuite struct {
	suite.Suite
	originalOutput *os.File
	logBuffer      *bytes.Buffer
}

func (suite *DeprecationTestSuite) SetupTest() {
	// Capture log output
	suite.logBuffer = &bytes.Buffer{}
	log.SetOutput(suite.logBuffer)
	log.SetFlags(0) // Remove timestamp for easier testing

	// Reset deprecation config to default
	deprecation.SetDeprecationConfig(deprecation.DefaultDeprecationConfig())
}

func (suite *DeprecationTestSuite) TearDownTest() {
	// Restore original log output
	log.SetOutput(os.Stderr)
	log.SetFlags(log.LstdFlags)
}

// Test basic deprecation warning
func (suite *DeprecationTestSuite) TestBasicDeprecationWarning() {
	t := suite.T()

	// Call deprecated method
	deprecation.DeprecatedMethod("TestMethod", "This is a test", "NewMethod()", "1.0.0")()

	// Check log output
	output := suite.logBuffer.String()
	assert.Contains(t, output, "DEPRECATION WARNING", "Should contain deprecation warning")
	assert.Contains(t, output, "TestMethod", "Should contain method name")
	assert.Contains(t, output, "This is a test", "Should contain reason")
	assert.Contains(t, output, "NewMethod()", "Should contain replacement")
	assert.Contains(t, output, "1.0.0", "Should contain version")
}

// Test deprecation warning can be disabled
func (suite *DeprecationTestSuite) TestDeprecationCanBeDisabled() {
	t := suite.T()

	// Disable deprecation warnings
	config := &deprecation.DeprecationConfig{
		Enabled: false,
	}
	deprecation.SetDeprecationConfig(config)

	// Call deprecated method
	deprecation.DeprecatedMethod("TestMethod", "This is a test", "NewMethod()", "1.0.0")()

	// Check that no output was generated
	output := suite.logBuffer.String()
	assert.Empty(t, output, "Should not generate output when disabled")
}

// Test deprecation configuration
func (suite *DeprecationTestSuite) TestDeprecationConfiguration() {
	t := suite.T()

	// Test default configuration
	defaultConfig := deprecation.DefaultDeprecationConfig()
	assert.True(t, defaultConfig.Enabled, "Default config should be enabled")
	assert.Equal(t, deprecation.DeprecationWarning, defaultConfig.Level, "Default level should be warning")
	assert.False(t, defaultConfig.ShowStackTrace, "Default should not show stack trace")

	// Test setting custom configuration
	customConfig := &deprecation.DeprecationConfig{
		Enabled:        false,
		Level:          deprecation.DeprecationError,
		ShowStackTrace: true,
	}
	deprecation.SetDeprecationConfig(customConfig)

	retrievedConfig := deprecation.GetDeprecationConfig()
	assert.Equal(t, customConfig.Enabled, retrievedConfig.Enabled)
	assert.Equal(t, customConfig.Level, retrievedConfig.Level)
	assert.Equal(t, customConfig.ShowStackTrace, retrievedConfig.ShowStackTrace)
}

// Test stack trace functionality
func (suite *DeprecationTestSuite) TestStackTraceFeature() {
	t := suite.T()

	// Enable stack trace
	config := &deprecation.DeprecationConfig{
		Enabled:        true,
		Level:          deprecation.DeprecationWarning,
		ShowStackTrace: true,
	}
	deprecation.SetDeprecationConfig(config)

	// Call deprecated method
	deprecation.Deprecated("This is deprecated", "Use new method", "2.0.0")

	// Check log output contains stack trace
	output := suite.logBuffer.String()
	assert.Contains(t, output, "Stack trace:", "Should contain stack trace header")
	assert.Contains(t, output, "deprecation_test.go", "Should contain test file in stack trace")
}

// Test deprecation without replacement
func (suite *DeprecationTestSuite) TestDeprecationWithoutReplacement() {
	t := suite.T()

	// Call deprecated method without replacement
	deprecation.DeprecatedMethod("OldMethod", "No longer supported", "", "2.0.0")()

	// Check log output
	output := suite.logBuffer.String()
	assert.Contains(t, output, "OldMethod", "Should contain method name")
	assert.Contains(t, output, "No longer supported", "Should contain reason")
	assert.NotContains(t, output, "Use OldMethod instead", "Should not contain replacement text when no replacement")
}

// Test deprecation without version
func (suite *DeprecationTestSuite) TestDeprecationWithoutVersion() {
	t := suite.T()

	// Call deprecated method without version
	deprecation.DeprecatedMethod("OldMethod", "No longer supported", "NewMethod()", "")()

	// Check log output
	output := suite.logBuffer.String()
	assert.Contains(t, output, "OldMethod", "Should contain method name")
	assert.NotContains(t, output, "since version", "Should not contain version info when empty")
}

// Test multiple deprecation calls
func (suite *DeprecationTestSuite) TestMultipleDeprecationCalls() {
	t := suite.T()

	// Call multiple deprecated methods
	deprecation.DeprecatedMethod("Method1", "Reason1", "NewMethod1()", "1.0.0")()
	deprecation.DeprecatedMethod("Method2", "Reason2", "NewMethod2()", "1.1.0")()
	deprecation.DeprecatedMethod("Method3", "Reason3", "NewMethod3()", "1.2.0")()

	// Check log output contains all warnings
	output := suite.logBuffer.String()
	lines := strings.Split(strings.TrimSpace(output), "\n")
	assert.Len(t, lines, 3, "Should have 3 deprecation warnings")

	assert.Contains(t, output, "Method1", "Should contain first method")
	assert.Contains(t, output, "Method2", "Should contain second method")
	assert.Contains(t, output, "Method3", "Should contain third method")
}

// Test deprecation level configuration
func (suite *DeprecationTestSuite) TestDeprecationLevels() {
	t := suite.T()

	// Test warning level (default)
	config := &deprecation.DeprecationConfig{
		Enabled: true,
		Level:   deprecation.DeprecationWarning,
	}
	deprecation.SetDeprecationConfig(config)

	deprecation.DeprecatedMethod("WarningMethod", "Test warning", "NewMethod()", "1.0.0")()

	output := suite.logBuffer.String()
	assert.Contains(t, output, "[DEPRECATION]", "Warning level should use [DEPRECATION] prefix")

	// Clear buffer for next test
	suite.logBuffer.Reset()

	// Test error level
	config.Level = deprecation.DeprecationError
	deprecation.SetDeprecationConfig(config)

	// Capture stderr for error level
	stderrBuffer := &bytes.Buffer{}
	originalStderr := os.Stderr
	r, w, _ := os.Pipe()
	os.Stderr = w

	go func() {
		buf := make([]byte, 1024)
		n, _ := r.Read(buf)
		stderrBuffer.Write(buf[:n])
		w.Close()
	}()

	deprecation.DeprecatedMethod("ErrorMethod", "Test error", "NewMethod()", "1.0.0")()

	w.Close()
	os.Stderr = originalStderr

	// Note: Error level output goes to stderr, not the log buffer
	// This test mainly ensures no panic occurs with error level
	assert.NotPanics(t, func() {
		deprecation.DeprecatedMethod("ErrorMethod2", "Test error 2", "NewMethod()", "1.0.0")()
	}, "Error level should not panic")
}

// Test concurrent deprecation calls
func (suite *DeprecationTestSuite) TestConcurrentDeprecationCalls() {
	t := suite.T()

	// Test that concurrent calls don't cause race conditions
	done := make(chan bool, 10)

	for i := 0; i < 10; i++ {
		go func(id int) {
			deprecation.DeprecatedMethod(
				fmt.Sprintf("Method%d", id),
				fmt.Sprintf("Reason%d", id),
				fmt.Sprintf("NewMethod%d()", id),
				"1.0.0",
			)()
			done <- true
		}(i)
	}

	// Wait for all goroutines to complete
	for i := 0; i < 10; i++ {
		<-done
	}

	// Check that output was generated (exact content may vary due to concurrency)
	output := suite.logBuffer.String()
	assert.NotEmpty(t, output, "Should generate some deprecation output")
	assert.Contains(t, output, "DEPRECATION WARNING", "Should contain deprecation warnings")
}

// Test edge cases
func (suite *DeprecationTestSuite) TestEdgeCases() {
	t := suite.T()

	// Test with empty strings
	assert.NotPanics(t, func() {
		deprecation.DeprecatedMethod("", "", "", "")()
	}, "Should not panic with empty strings")

	// Test with very long strings
	longString := strings.Repeat("a", 1000)
	assert.NotPanics(t, func() {
		deprecation.DeprecatedMethod(longString, longString, longString, longString)()
	}, "Should not panic with long strings")

	// Test with special characters
	assert.NotPanics(t, func() {
		deprecation.DeprecatedMethod("Method@#$%", "Reason with 中文 and émojis 🚀", "NewMethod()", "1.0.0")()
	}, "Should not panic with special characters")
}

// Run the test suite
func TestDeprecationTestSuite(t *testing.T) {
	suite.Run(t, new(DeprecationTestSuite))
}
