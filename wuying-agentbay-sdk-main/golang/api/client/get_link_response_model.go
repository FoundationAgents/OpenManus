// This file is auto-generated, don't edit it. Thanks.
package client

import (
	"github.com/alibabacloud-go/tea/dara"
)

type iGetLinkResponse interface {
	dara.Model
	String() string
	GoString() string
	SetHeaders(v map[string]*string) *GetLinkResponse
	GetHeaders() map[string]*string
	SetStatusCode(v int32) *GetLinkResponse
	GetStatusCode() *int32
	SetBody(v *GetLinkResponseBody) *GetLinkResponse
	GetBody() *GetLinkResponseBody
}

type GetLinkResponse struct {
	Headers    map[string]*string   `json:"headers,omitempty" xml:"headers,omitempty"`
	StatusCode *int32               `json:"statusCode,omitempty" xml:"statusCode,omitempty"`
	Body       *GetLinkResponseBody `json:"body,omitempty" xml:"body,omitempty"`
}

func (s GetLinkResponse) String() string {
	return dara.Prettify(s)
}

func (s GetLinkResponse) GoString() string {
	return s.String()
}

func (s *GetLinkResponse) GetHeaders() map[string]*string {
	return s.Headers
}

func (s *GetLinkResponse) GetStatusCode() *int32 {
	return s.StatusCode
}

func (s *GetLinkResponse) GetBody() *GetLinkResponseBody {
	return s.Body
}

func (s *GetLinkResponse) SetHeaders(v map[string]*string) *GetLinkResponse {
	s.Headers = v
	return s
}

func (s *GetLinkResponse) SetStatusCode(v int32) *GetLinkResponse {
	s.StatusCode = &v
	return s
}

func (s *GetLinkResponse) SetBody(v *GetLinkResponseBody) *GetLinkResponse {
	s.Body = v
	return s
}

func (s *GetLinkResponse) Validate() error {
	return dara.Validate(s)
}
