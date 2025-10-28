package agentbay

import (
	"fmt"
	"log"
	"os"
	"runtime"
)

// DeprecationLevel represents the level of deprecation warning
type DeprecationLevel int

const (
	// DeprecationWarning represents a standard deprecation warning
	DeprecationWarning DeprecationLevel = iota
	// DeprecationError represents a deprecation that should be treated as an error
	DeprecationError
)

// DeprecationConfig holds configuration for deprecation warnings
type DeprecationConfig struct {
	// Enabled controls whether deprecation warnings are shown
	Enabled bool
	// Level controls the severity of deprecation warnings
	Level DeprecationLevel
	// ShowStackTrace controls whether to show stack trace in warnings
	ShowStackTrace bool
}

// DefaultDeprecationConfig returns the default deprecation configuration
func DefaultDeprecationConfig() *DeprecationConfig {
	return &DeprecationConfig{
		Enabled:        true,
		Level:          DeprecationWarning,
		ShowStackTrace: false,
	}
}

// globalDeprecationConfig holds the global deprecation configuration
var globalDeprecationConfig = DefaultDeprecationConfig()

// SetDeprecationConfig sets the global deprecation configuration
func SetDeprecationConfig(config *DeprecationConfig) {
	globalDeprecationConfig = config
}

// GetDeprecationConfig returns the current global deprecation configuration
func GetDeprecationConfig() *DeprecationConfig {
	return globalDeprecationConfig
}

// Deprecated marks a function or method as deprecated and emits a warning
func Deprecated(reason, replacement, version string) {
	if !globalDeprecationConfig.Enabled {
		return
	}

	// Get caller information
	pc, file, line, ok := runtime.Caller(1)
	var funcName string
	if ok {
		fn := runtime.FuncForPC(pc)
		if fn != nil {
			funcName = fn.Name()
		}
	}

	// Build deprecation message
	message := fmt.Sprintf("DEPRECATION WARNING: %s is deprecated", funcName)
	if version != "" {
		message += fmt.Sprintf(" since version %s", version)
	}
	message += fmt.Sprintf(". %s", reason)
	if replacement != "" {
		message += fmt.Sprintf(" Use %s instead.", replacement)
	}

	// Add location information if available
	if ok {
		message += fmt.Sprintf(" (called from %s:%d)", file, line)
	}

	// Show stack trace if enabled
	if globalDeprecationConfig.ShowStackTrace {
		message += "\nStack trace:"
		for i := 1; i < 10; i++ {
			pc, file, line, ok := runtime.Caller(i)
			if !ok {
				break
			}
			fn := runtime.FuncForPC(pc)
			if fn != nil {
				message += fmt.Sprintf("\n  %s:%d %s", file, line, fn.Name())
			}
		}
	}

	// Output the warning
	switch globalDeprecationConfig.Level {
	case DeprecationWarning:
		log.Printf("[DEPRECATION] %s\n", message)
	case DeprecationError:
		fmt.Fprintf(os.Stderr, "[DEPRECATION ERROR] %s\n", message)
	}
}

// DeprecatedFunc is a helper function to mark functions as deprecated
// Usage: defer DeprecatedFunc("reason", "replacement", "version")()
func DeprecatedFunc(reason, replacement, version string) func() {
	return func() {
		Deprecated(reason, replacement, version)
	}
}

// DeprecatedMethod is a helper function to mark methods as deprecated
// Usage: defer DeprecatedMethod("MethodName", "reason", "replacement", "version")()
func DeprecatedMethod(methodName, reason, replacement, version string) func() {
	return func() {
		if !globalDeprecationConfig.Enabled {
			return
		}

		// Build deprecation message
		message := fmt.Sprintf("DEPRECATION WARNING: %s is deprecated", methodName)
		if version != "" {
			message += fmt.Sprintf(" since version %s", version)
		}
		message += fmt.Sprintf(". %s", reason)
		if replacement != "" {
			message += fmt.Sprintf(" Use %s instead.", replacement)
		}

		// Get caller information
		_, file, line, ok := runtime.Caller(2) // Skip one more frame since this is called from a defer
		if ok {
			message += fmt.Sprintf(" (called from %s:%d)", file, line)
		}

		// Output the warning
		switch globalDeprecationConfig.Level {
		case DeprecationWarning:
			log.Printf("[DEPRECATION] %s\n", message)
		case DeprecationError:
			fmt.Fprintf(os.Stderr, "[DEPRECATION ERROR] %s\n", message)
		}
	}
}
