// This file is auto-generated, don't edit it. Thanks.
package client

import (
	"github.com/alibabacloud-go/tea/dara"
)

type iCallMcpToolResponse interface {
	dara.Model
	String() string
	GoString() string
	SetHeaders(v map[string]*string) *CallMcpToolResponse
	GetHeaders() map[string]*string
	SetStatusCode(v int32) *CallMcpToolResponse
	GetStatusCode() *int32
	SetBody(v *CallMcpToolResponseBody) *CallMcpToolResponse
	GetBody() *CallMcpToolResponseBody
}

type CallMcpToolResponse struct {
	Headers    map[string]*string       `json:"headers,omitempty" xml:"headers,omitempty"`
	StatusCode *int32                   `json:"statusCode,omitempty" xml:"statusCode,omitempty"`
	Body       *CallMcpToolResponseBody `json:"body,omitempty" xml:"body,omitempty"`
}

func (s CallMcpToolResponse) String() string {
	return dara.Prettify(s)
}

func (s CallMcpToolResponse) GoString() string {
	return s.String()
}

func (s *CallMcpToolResponse) GetHeaders() map[string]*string {
	return s.Headers
}

func (s *CallMcpToolResponse) GetStatusCode() *int32 {
	return s.StatusCode
}

func (s *CallMcpToolResponse) GetBody() *CallMcpToolResponseBody {
	return s.Body
}

func (s *CallMcpToolResponse) SetHeaders(v map[string]*string) *CallMcpToolResponse {
	s.Headers = v
	return s
}

func (s *CallMcpToolResponse) SetStatusCode(v int32) *CallMcpToolResponse {
	s.StatusCode = &v
	return s
}

func (s *CallMcpToolResponse) SetBody(v *CallMcpToolResponseBody) *CallMcpToolResponse {
	s.Body = v
	return s
}

func (s *CallMcpToolResponse) Validate() error {
	return dara.Validate(s)
}
