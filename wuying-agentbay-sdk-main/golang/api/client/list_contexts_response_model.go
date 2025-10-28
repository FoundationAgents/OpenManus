// This file is auto-generated, don't edit it. Thanks.
package client

import (
	"github.com/alibabacloud-go/tea/dara"
)

type iListContextsResponse interface {
	dara.Model
	String() string
	GoString() string
	SetHeaders(v map[string]*string) *ListContextsResponse
	GetHeaders() map[string]*string
	SetStatusCode(v int32) *ListContextsResponse
	GetStatusCode() *int32
	SetBody(v *ListContextsResponseBody) *ListContextsResponse
	GetBody() *ListContextsResponseBody
}

type ListContextsResponse struct {
	Headers    map[string]*string        `json:"headers,omitempty" xml:"headers,omitempty"`
	StatusCode *int32                    `json:"statusCode,omitempty" xml:"statusCode,omitempty"`
	Body       *ListContextsResponseBody `json:"body,omitempty" xml:"body,omitempty"`
}

func (s ListContextsResponse) String() string {
	return dara.Prettify(s)
}

func (s ListContextsResponse) GoString() string {
	return s.String()
}

func (s *ListContextsResponse) GetHeaders() map[string]*string {
	return s.Headers
}

func (s *ListContextsResponse) GetStatusCode() *int32 {
	return s.StatusCode
}

func (s *ListContextsResponse) GetBody() *ListContextsResponseBody {
	return s.Body
}

func (s *ListContextsResponse) SetHeaders(v map[string]*string) *ListContextsResponse {
	s.Headers = v
	return s
}

func (s *ListContextsResponse) SetStatusCode(v int32) *ListContextsResponse {
	s.StatusCode = &v
	return s
}

func (s *ListContextsResponse) SetBody(v *ListContextsResponseBody) *ListContextsResponse {
	s.Body = v
	return s
}

func (s *ListContextsResponse) Validate() error {
	return dara.Validate(s)
}
