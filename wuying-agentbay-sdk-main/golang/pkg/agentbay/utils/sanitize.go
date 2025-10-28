package utils

import (
	"regexp"
)

// SanitizeError sanitizes error messages to remove sensitive information like API keys
func SanitizeError(err error) string {
	if err == nil {
		return ""
	}

	errStr := err.Error()

	// Remove API key from URLs
	// Pattern: apiKey=akm-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
	apiKeyPattern := regexp.MustCompile(`apiKey=akm-[a-f0-9-]+`)
	errStr = apiKeyPattern.ReplaceAllString(errStr, "apiKey=***REDACTED***")

	// Remove API key from Bearer tokens
	// Pattern: Bearer akm-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
	bearerPattern := regexp.MustCompile(`Bearer akm-[a-f0-9-]+`)
	errStr = bearerPattern.ReplaceAllString(errStr, "Bearer ***REDACTED***")

	// Remove API key from query parameters
	// Pattern: &apiKey=akm-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
	queryPattern := regexp.MustCompile(`&apiKey=akm-[a-f0-9-]+`)
	errStr = queryPattern.ReplaceAllString(errStr, "&apiKey=***REDACTED***")

	// Remove API key from URL paths
	// Pattern: /callTool?apiKey=akm-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
	urlPattern := regexp.MustCompile(`/callTool\?apiKey=akm-[a-f0-9-]+`)
	errStr = urlPattern.ReplaceAllString(errStr, "/callTool?apiKey=***REDACTED***")

	return errStr
}

// SanitizeURL sanitizes URLs to remove sensitive information
func SanitizeURL(url string) string {
	if url == "" {
		return url
	}

	// Remove API key from query parameters
	apiKeyPattern := regexp.MustCompile(`apiKey=akm-[a-f0-9-]+`)
	return apiKeyPattern.ReplaceAllString(url, "apiKey=***REDACTED***")
}

// SanitizeString sanitizes any string to remove sensitive information
func SanitizeString(s string) string {
	if s == "" {
		return s
	}

	// Remove API key patterns
	apiKeyPattern := regexp.MustCompile(`akm-[a-f0-9-]+`)
	return apiKeyPattern.ReplaceAllString(s, "***REDACTED***")
}
