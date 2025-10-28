// This file is auto-generated, don't edit it. Thanks.
package client

import (
	"github.com/alibabacloud-go/tea/dara"
)

type iGetContextResponse interface {
	dara.Model
	String() string
	GoString() string
	SetHeaders(v map[string]*string) *GetContextResponse
	GetHeaders() map[string]*string
	SetStatusCode(v int32) *GetContextResponse
	GetStatusCode() *int32
	SetBody(v *GetContextResponseBody) *GetContextResponse
	GetBody() *GetContextResponseBody
}

type GetContextResponse struct {
	Headers    map[string]*string      `json:"headers,omitempty" xml:"headers,omitempty"`
	StatusCode *int32                  `json:"statusCode,omitempty" xml:"statusCode,omitempty"`
	Body       *GetContextResponseBody `json:"body,omitempty" xml:"body,omitempty"`
}

func (s GetContextResponse) String() string {
	return dara.Prettify(s)
}

func (s GetContextResponse) GoString() string {
	return s.String()
}

func (s *GetContextResponse) GetHeaders() map[string]*string {
	return s.Headers
}

func (s *GetContextResponse) GetStatusCode() *int32 {
	return s.StatusCode
}

func (s *GetContextResponse) GetBody() *GetContextResponseBody {
	return s.Body
}

func (s *GetContextResponse) SetHeaders(v map[string]*string) *GetContextResponse {
	s.Headers = v
	return s
}

func (s *GetContextResponse) SetStatusCode(v int32) *GetContextResponse {
	s.StatusCode = &v
	return s
}

func (s *GetContextResponse) SetBody(v *GetContextResponseBody) *GetContextResponse {
	s.Body = v
	return s
}

func (s *GetContextResponse) Validate() error {
	return dara.Validate(s)
}
