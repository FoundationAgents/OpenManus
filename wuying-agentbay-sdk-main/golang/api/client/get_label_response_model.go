// This file is auto-generated, don't edit it. Thanks.
package client

import (
	"github.com/alibabacloud-go/tea/dara"
)

type iGetLabelResponse interface {
	dara.Model
	String() string
	GoString() string
	SetHeaders(v map[string]*string) *GetLabelResponse
	GetHeaders() map[string]*string
	SetStatusCode(v int32) *GetLabelResponse
	GetStatusCode() *int32
	SetBody(v *GetLabelResponseBody) *GetLabelResponse
	GetBody() *GetLabelResponseBody
}

type GetLabelResponse struct {
	Headers    map[string]*string    `json:"headers,omitempty" xml:"headers,omitempty"`
	StatusCode *int32                `json:"statusCode,omitempty" xml:"statusCode,omitempty"`
	Body       *GetLabelResponseBody `json:"body,omitempty" xml:"body,omitempty"`
}

func (s GetLabelResponse) String() string {
	return dara.Prettify(s)
}

func (s GetLabelResponse) GoString() string {
	return s.String()
}

func (s *GetLabelResponse) GetHeaders() map[string]*string {
	return s.Headers
}

func (s *GetLabelResponse) GetStatusCode() *int32 {
	return s.StatusCode
}

func (s *GetLabelResponse) GetBody() *GetLabelResponseBody {
	return s.Body
}

func (s *GetLabelResponse) SetHeaders(v map[string]*string) *GetLabelResponse {
	s.Headers = v
	return s
}

func (s *GetLabelResponse) SetStatusCode(v int32) *GetLabelResponse {
	s.StatusCode = &v
	return s
}

func (s *GetLabelResponse) SetBody(v *GetLabelResponseBody) *GetLabelResponse {
	s.Body = v
	return s
}

func (s *GetLabelResponse) Validate() error {
	return dara.Validate(s)
}
