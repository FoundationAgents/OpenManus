// This file is auto-generated, don't edit it. Thanks.
package client

import (
	"github.com/alibabacloud-go/tea/dara"
)

type iSetLabelResponse interface {
	dara.Model
	String() string
	GoString() string
	SetHeaders(v map[string]*string) *SetLabelResponse
	GetHeaders() map[string]*string
	SetStatusCode(v int32) *SetLabelResponse
	GetStatusCode() *int32
	SetBody(v *SetLabelResponseBody) *SetLabelResponse
	GetBody() *SetLabelResponseBody
}

type SetLabelResponse struct {
	Headers    map[string]*string    `json:"headers,omitempty" xml:"headers,omitempty"`
	StatusCode *int32                `json:"statusCode,omitempty" xml:"statusCode,omitempty"`
	Body       *SetLabelResponseBody `json:"body,omitempty" xml:"body,omitempty"`
}

func (s SetLabelResponse) String() string {
	return dara.Prettify(s)
}

func (s SetLabelResponse) GoString() string {
	return s.String()
}

func (s *SetLabelResponse) GetHeaders() map[string]*string {
	return s.Headers
}

func (s *SetLabelResponse) GetStatusCode() *int32 {
	return s.StatusCode
}

func (s *SetLabelResponse) GetBody() *SetLabelResponseBody {
	return s.Body
}

func (s *SetLabelResponse) SetHeaders(v map[string]*string) *SetLabelResponse {
	s.Headers = v
	return s
}

func (s *SetLabelResponse) SetStatusCode(v int32) *SetLabelResponse {
	s.StatusCode = &v
	return s
}

func (s *SetLabelResponse) SetBody(v *SetLabelResponseBody) *SetLabelResponse {
	s.Body = v
	return s
}

func (s *SetLabelResponse) Validate() error {
	return dara.Validate(s)
}
