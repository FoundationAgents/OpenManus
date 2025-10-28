// This file is auto-generated, don't edit it. Thanks.
package client

import (
	"github.com/alibabacloud-go/tea/dara"
)

type iGetMcpResourceResponse interface {
	dara.Model
	String() string
	GoString() string
	SetHeaders(v map[string]*string) *GetMcpResourceResponse
	GetHeaders() map[string]*string
	SetStatusCode(v int32) *GetMcpResourceResponse
	GetStatusCode() *int32
	SetBody(v *GetMcpResourceResponseBody) *GetMcpResourceResponse
	GetBody() *GetMcpResourceResponseBody
}

type GetMcpResourceResponse struct {
	Headers    map[string]*string          `json:"headers,omitempty" xml:"headers,omitempty"`
	StatusCode *int32                      `json:"statusCode,omitempty" xml:"statusCode,omitempty"`
	Body       *GetMcpResourceResponseBody `json:"body,omitempty" xml:"body,omitempty"`
}

func (s GetMcpResourceResponse) String() string {
	return dara.Prettify(s)
}

func (s GetMcpResourceResponse) GoString() string {
	return s.String()
}

func (s *GetMcpResourceResponse) GetHeaders() map[string]*string {
	return s.Headers
}

func (s *GetMcpResourceResponse) GetStatusCode() *int32 {
	return s.StatusCode
}

func (s *GetMcpResourceResponse) GetBody() *GetMcpResourceResponseBody {
	return s.Body
}

func (s *GetMcpResourceResponse) SetHeaders(v map[string]*string) *GetMcpResourceResponse {
	s.Headers = v
	return s
}

func (s *GetMcpResourceResponse) SetStatusCode(v int32) *GetMcpResourceResponse {
	s.StatusCode = &v
	return s
}

func (s *GetMcpResourceResponse) SetBody(v *GetMcpResourceResponseBody) *GetMcpResourceResponse {
	s.Body = v
	return s
}

func (s *GetMcpResourceResponse) Validate() error {
	return dara.Validate(s)
}
