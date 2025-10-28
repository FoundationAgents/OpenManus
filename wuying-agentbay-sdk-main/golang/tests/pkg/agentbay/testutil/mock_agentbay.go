package testutil

import (
	"github.com/aliyun/wuying-agentbay-sdk/golang/api/client"
	"github.com/stretchr/testify/mock"
)

// MockAgentBay is a mock implementation of AgentBay for testing
type MockAgentBay struct {
	mock.Mock
}

// GetAPIKey mocks the GetAPIKey method
func (m *MockAgentBay) GetAPIKey() string {
	args := m.Called()
	return args.String(0)
}

// GetClient mocks the GetClient method
func (m *MockAgentBay) GetClient() *client.Client {
	args := m.Called()
	return args.Get(0).(*client.Client)
}

// Sessions mocks the Sessions field
func (m *MockAgentBay) Sessions() interface{} {
	args := m.Called()
	return args.Get(0)
}

// MockClient is a mock implementation of the client for testing
type MockClient struct {
	mock.Mock
}

// ReleaseMcpSession mocks the ReleaseMcpSession method
func (m *MockClient) ReleaseMcpSession(request *client.ReleaseMcpSessionRequest) (*client.ReleaseMcpSessionResponse, error) {
	args := m.Called(request)
	if args.Get(0) == nil {
		return nil, args.Error(1)
	}
	return args.Get(0).(*client.ReleaseMcpSessionResponse), args.Error(1)
}

// CreateMockReleaseMcpSessionResponse creates a mock response for ReleaseMcpSession
func CreateMockReleaseMcpSessionResponse(success bool, requestID string) *client.ReleaseMcpSessionResponse {
	response := &client.ReleaseMcpSessionResponse{}
	response.Body = &client.ReleaseMcpSessionResponseBody{
		RequestId: &requestID,
		Success:   &success,
	}
	return response
}
