package models

import (
	"reflect"
)

// ApiResponse is the base class for all API responses, containing RequestID
type ApiResponse struct {
	RequestID string // Unique identifier for the API request
}

// GetRequestID returns the unique identifier for the API request
func (a ApiResponse) GetRequestID() string {
	return a.RequestID
}

// WithRequestID creates a new ApiResponse with the specified RequestID
func WithRequestID(requestID string) ApiResponse {
	return ApiResponse{
		RequestID: requestID,
	}
}

// ExtractRequestID extracts RequestID from API response
// This is a helper function used to extract RequestID in all API methods
func ExtractRequestID(response interface{}) string {
	if response == nil {
		return ""
	}

	// Use reflection to extract RequestId from different response structures
	v := reflect.ValueOf(response)
	if v.Kind() == reflect.Ptr {
		if v.IsNil() {
			return ""
		}
		v = v.Elem()
	}

	// Check if there is a Body field containing RequestId
	if v.Kind() == reflect.Struct && v.FieldByName("Body").IsValid() {
		body := v.FieldByName("Body")
		if body.IsValid() && body.Kind() == reflect.Ptr && !body.IsNil() {
			bodyVal := body.Elem()
			reqID := bodyVal.FieldByName("RequestId")
			if reqID.IsValid() && reqID.Kind() == reflect.Ptr && !reqID.IsNil() {
				return reqID.Elem().String()
			}
		}
	}

	return ""
}

// McpToolResult represents the result of an MCP tool call for Agent
type McpToolResult struct {
	Success      bool   `json:"success"`
	Data         string `json:"data"`
	ErrorMessage string `json:"error_message"`
	RequestID    string `json:"request_id"`
}
