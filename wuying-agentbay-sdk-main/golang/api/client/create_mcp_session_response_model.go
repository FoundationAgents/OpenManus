// This file is auto-generated, don't edit it. Thanks.
package client

import (
	"github.com/alibabacloud-go/tea/dara"
)

type iCreateMcpSessionResponse interface {
	dara.Model
	String() string
	GoString() string
	SetHeaders(v map[string]*string) *CreateMcpSessionResponse
	GetHeaders() map[string]*string
	SetStatusCode(v int32) *CreateMcpSessionResponse
	GetStatusCode() *int32
	SetBody(v *CreateMcpSessionResponseBody) *CreateMcpSessionResponse
	GetBody() *CreateMcpSessionResponseBody
}

type CreateMcpSessionResponse struct {
	Headers    map[string]*string            `json:"headers,omitempty" xml:"headers,omitempty"`
	StatusCode *int32                        `json:"statusCode,omitempty" xml:"statusCode,omitempty"`
	Body       *CreateMcpSessionResponseBody `json:"body,omitempty" xml:"body,omitempty"`
}

func (s CreateMcpSessionResponse) String() string {
	return dara.Prettify(s)
}

func (s CreateMcpSessionResponse) GoString() string {
	return s.String()
}

func (s *CreateMcpSessionResponse) GetHeaders() map[string]*string {
	return s.Headers
}

func (s *CreateMcpSessionResponse) GetStatusCode() *int32 {
	return s.StatusCode
}

func (s *CreateMcpSessionResponse) GetBody() *CreateMcpSessionResponseBody {
	return s.Body
}

func (s *CreateMcpSessionResponse) SetHeaders(v map[string]*string) *CreateMcpSessionResponse {
	s.Headers = v
	return s
}

func (s *CreateMcpSessionResponse) SetStatusCode(v int32) *CreateMcpSessionResponse {
	s.StatusCode = &v
	return s
}

func (s *CreateMcpSessionResponse) SetBody(v *CreateMcpSessionResponseBody) *CreateMcpSessionResponse {
	s.Body = v
	return s
}

func (s *CreateMcpSessionResponse) Validate() error {
	return dara.Validate(s)
}
