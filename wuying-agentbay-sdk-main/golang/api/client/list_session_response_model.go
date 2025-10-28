// This file is auto-generated, don't edit it. Thanks.
package client

import (
	"github.com/alibabacloud-go/tea/dara"
)

type iListSessionResponse interface {
	dara.Model
	String() string
	GoString() string
	SetHeaders(v map[string]*string) *ListSessionResponse
	GetHeaders() map[string]*string
	SetStatusCode(v int32) *ListSessionResponse
	GetStatusCode() *int32
	SetBody(v *ListSessionResponseBody) *ListSessionResponse
	GetBody() *ListSessionResponseBody
}

type ListSessionResponse struct {
	Headers    map[string]*string       `json:"headers,omitempty" xml:"headers,omitempty"`
	StatusCode *int32                   `json:"statusCode,omitempty" xml:"statusCode,omitempty"`
	Body       *ListSessionResponseBody `json:"body,omitempty" xml:"body,omitempty"`
}

func (s ListSessionResponse) String() string {
	return dara.Prettify(s)
}

func (s ListSessionResponse) GoString() string {
	return s.String()
}

func (s *ListSessionResponse) GetHeaders() map[string]*string {
	return s.Headers
}

func (s *ListSessionResponse) GetStatusCode() *int32 {
	return s.StatusCode
}

func (s *ListSessionResponse) GetBody() *ListSessionResponseBody {
	return s.Body
}

func (s *ListSessionResponse) SetHeaders(v map[string]*string) *ListSessionResponse {
	s.Headers = v
	return s
}

func (s *ListSessionResponse) SetStatusCode(v int32) *ListSessionResponse {
	s.StatusCode = &v
	return s
}

func (s *ListSessionResponse) SetBody(v *ListSessionResponseBody) *ListSessionResponse {
	s.Body = v
	return s
}

func (s *ListSessionResponse) Validate() error {
	return dara.Validate(s)
}
