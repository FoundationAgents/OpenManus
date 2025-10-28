// This file is auto-generated, don't edit it. Thanks.
package client

import (
	"github.com/alibabacloud-go/tea/dara"
)

type iModifyContextResponse interface {
	dara.Model
	String() string
	GoString() string
	SetHeaders(v map[string]*string) *ModifyContextResponse
	GetHeaders() map[string]*string
	SetStatusCode(v int32) *ModifyContextResponse
	GetStatusCode() *int32
	SetBody(v *ModifyContextResponseBody) *ModifyContextResponse
	GetBody() *ModifyContextResponseBody
}

type ModifyContextResponse struct {
	Headers    map[string]*string         `json:"headers,omitempty" xml:"headers,omitempty"`
	StatusCode *int32                     `json:"statusCode,omitempty" xml:"statusCode,omitempty"`
	Body       *ModifyContextResponseBody `json:"body,omitempty" xml:"body,omitempty"`
}

func (s ModifyContextResponse) String() string {
	return dara.Prettify(s)
}

func (s ModifyContextResponse) GoString() string {
	return s.String()
}

func (s *ModifyContextResponse) GetHeaders() map[string]*string {
	return s.Headers
}

func (s *ModifyContextResponse) GetStatusCode() *int32 {
	return s.StatusCode
}

func (s *ModifyContextResponse) GetBody() *ModifyContextResponseBody {
	return s.Body
}

func (s *ModifyContextResponse) SetHeaders(v map[string]*string) *ModifyContextResponse {
	s.Headers = v
	return s
}

func (s *ModifyContextResponse) SetStatusCode(v int32) *ModifyContextResponse {
	s.StatusCode = &v
	return s
}

func (s *ModifyContextResponse) SetBody(v *ModifyContextResponseBody) *ModifyContextResponse {
	s.Body = v
	return s
}

func (s *ModifyContextResponse) Validate() error {
	return dara.Validate(s)
}
