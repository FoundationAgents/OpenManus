package agentbay_test

import (
	"testing"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
)

func TestSession_ValidateLabels(t *testing.T) {
	// Create a real session to access the ValidateLabels method
	// We'll create a minimal session with just the needed fields
	realSession := &agentbay.Session{}

	// Test cases
	tests := []struct {
		name     string
		labels   map[string]string
		expected string
	}{
		{
			name:     "ValidLabels",
			labels:   map[string]string{"key1": "value1", "key2": "value2"},
			expected: "",
		},
		{
			name:     "NilLabels",
			labels:   nil,
			expected: "Labels cannot be nil. Please provide a valid labels map.",
		},
		{
			name:     "EmptyLabels",
			labels:   map[string]string{},
			expected: "Labels cannot be empty. Please provide at least one label.",
		},
		{
			name:     "EmptyKey",
			labels:   map[string]string{"": "value1"},
			expected: "Label keys cannot be empty. Please provide valid keys.",
		},
		{
			name:     "EmptyValue",
			labels:   map[string]string{"key1": ""},
			expected: "Label values cannot be empty. Please provide valid values.",
		},
	}

	// Run test cases
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			// Call the ValidateLabels method on the real session
			result := realSession.ValidateLabels(tt.labels)
			if result != tt.expected {
				t.Errorf("ValidateLabels() = %v, want %v", result, tt.expected)
			}
		})
	}
}
