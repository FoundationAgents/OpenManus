// This file is auto-generated, don't edit it. Thanks.
package client

import (
	"github.com/alibabacloud-go/tea/dara"
)

type iReleaseMcpSessionResponse interface {
	dara.Model
	String() string
	GoString() string
	SetHeaders(v map[string]*string) *ReleaseMcpSessionResponse
	GetHeaders() map[string]*string
	SetStatusCode(v int32) *ReleaseMcpSessionResponse
	GetStatusCode() *int32
	SetBody(v *ReleaseMcpSessionResponseBody) *ReleaseMcpSessionResponse
	GetBody() *ReleaseMcpSessionResponseBody
}

type ReleaseMcpSessionResponse struct {
	Headers    map[string]*string             `json:"headers,omitempty" xml:"headers,omitempty"`
	StatusCode *int32                         `json:"statusCode,omitempty" xml:"statusCode,omitempty"`
	Body       *ReleaseMcpSessionResponseBody `json:"body,omitempty" xml:"body,omitempty"`
}

func (s ReleaseMcpSessionResponse) String() string {
	return dara.Prettify(s)
}

func (s ReleaseMcpSessionResponse) GoString() string {
	return s.String()
}

func (s *ReleaseMcpSessionResponse) GetHeaders() map[string]*string {
	return s.Headers
}

func (s *ReleaseMcpSessionResponse) GetStatusCode() *int32 {
	return s.StatusCode
}

func (s *ReleaseMcpSessionResponse) GetBody() *ReleaseMcpSessionResponseBody {
	return s.Body
}

func (s *ReleaseMcpSessionResponse) SetHeaders(v map[string]*string) *ReleaseMcpSessionResponse {
	s.Headers = v
	return s
}

func (s *ReleaseMcpSessionResponse) SetStatusCode(v int32) *ReleaseMcpSessionResponse {
	s.StatusCode = &v
	return s
}

func (s *ReleaseMcpSessionResponse) SetBody(v *ReleaseMcpSessionResponseBody) *ReleaseMcpSessionResponse {
	s.Body = v
	return s
}

func (s *ReleaseMcpSessionResponse) Validate() error {
	return dara.Validate(s)
}
