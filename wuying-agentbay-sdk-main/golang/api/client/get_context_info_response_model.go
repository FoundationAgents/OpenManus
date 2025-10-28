// This file is auto-generated, don't edit it. Thanks.
package client

import (
	"github.com/alibabacloud-go/tea/dara"
)

type iGetContextInfoResponse interface {
	dara.Model
	String() string
	GoString() string
	SetHeaders(v map[string]*string) *GetContextInfoResponse
	GetHeaders() map[string]*string
	SetStatusCode(v int32) *GetContextInfoResponse
	GetStatusCode() *int32
	SetBody(v *GetContextInfoResponseBody) *GetContextInfoResponse
	GetBody() *GetContextInfoResponseBody
}

type GetContextInfoResponse struct {
	Headers    map[string]*string          `json:"headers,omitempty" xml:"headers,omitempty"`
	StatusCode *int32                      `json:"statusCode,omitempty" xml:"statusCode,omitempty"`
	Body       *GetContextInfoResponseBody `json:"body,omitempty" xml:"body,omitempty"`
}

func (s GetContextInfoResponse) String() string {
	return dara.Prettify(s)
}

func (s GetContextInfoResponse) GoString() string {
	return s.String()
}

func (s *GetContextInfoResponse) GetHeaders() map[string]*string {
	return s.Headers
}

func (s *GetContextInfoResponse) GetStatusCode() *int32 {
	return s.StatusCode
}

func (s *GetContextInfoResponse) GetBody() *GetContextInfoResponseBody {
	return s.Body
}

func (s *GetContextInfoResponse) SetHeaders(v map[string]*string) *GetContextInfoResponse {
	s.Headers = v
	return s
}

func (s *GetContextInfoResponse) SetStatusCode(v int32) *GetContextInfoResponse {
	s.StatusCode = &v
	return s
}

func (s *GetContextInfoResponse) SetBody(v *GetContextInfoResponseBody) *GetContextInfoResponse {
	s.Body = v
	return s
}

func (s *GetContextInfoResponse) Validate() error {
	return dara.Validate(s)
}
