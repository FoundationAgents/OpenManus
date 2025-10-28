// This file is auto-generated, don't edit it. Thanks.
package client

import (
	"github.com/alibabacloud-go/tea/dara"
)

type iListMcpToolsResponse interface {
	dara.Model
	String() string
	GoString() string
	SetHeaders(v map[string]*string) *ListMcpToolsResponse
	GetHeaders() map[string]*string
	SetStatusCode(v int32) *ListMcpToolsResponse
	GetStatusCode() *int32
	SetBody(v *ListMcpToolsResponseBody) *ListMcpToolsResponse
	GetBody() *ListMcpToolsResponseBody
}

type ListMcpToolsResponse struct {
	Headers    map[string]*string        `json:"headers,omitempty" xml:"headers,omitempty"`
	StatusCode *int32                    `json:"statusCode,omitempty" xml:"statusCode,omitempty"`
	Body       *ListMcpToolsResponseBody `json:"body,omitempty" xml:"body,omitempty"`
}

func (s ListMcpToolsResponse) String() string {
	return dara.Prettify(s)
}

func (s ListMcpToolsResponse) GoString() string {
	return s.String()
}

func (s *ListMcpToolsResponse) GetHeaders() map[string]*string {
	return s.Headers
}

func (s *ListMcpToolsResponse) GetStatusCode() *int32 {
	return s.StatusCode
}

func (s *ListMcpToolsResponse) GetBody() *ListMcpToolsResponseBody {
	return s.Body
}

func (s *ListMcpToolsResponse) SetHeaders(v map[string]*string) *ListMcpToolsResponse {
	s.Headers = v
	return s
}

func (s *ListMcpToolsResponse) SetStatusCode(v int32) *ListMcpToolsResponse {
	s.StatusCode = &v
	return s
}

func (s *ListMcpToolsResponse) SetBody(v *ListMcpToolsResponseBody) *ListMcpToolsResponse {
	s.Body = v
	return s
}

func (s *ListMcpToolsResponse) Validate() error {
	return dara.Validate(s)
}
