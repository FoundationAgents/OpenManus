// This file is auto-generated, don't edit it. Thanks.
package client

import (
	"github.com/alibabacloud-go/tea/dara"
)

type iDeleteContextResponse interface {
	dara.Model
	String() string
	GoString() string
	SetHeaders(v map[string]*string) *DeleteContextResponse
	GetHeaders() map[string]*string
	SetStatusCode(v int32) *DeleteContextResponse
	GetStatusCode() *int32
	SetBody(v *DeleteContextResponseBody) *DeleteContextResponse
	GetBody() *DeleteContextResponseBody
}

type DeleteContextResponse struct {
	Headers    map[string]*string         `json:"headers,omitempty" xml:"headers,omitempty"`
	StatusCode *int32                     `json:"statusCode,omitempty" xml:"statusCode,omitempty"`
	Body       *DeleteContextResponseBody `json:"body,omitempty" xml:"body,omitempty"`
}

func (s DeleteContextResponse) String() string {
	return dara.Prettify(s)
}

func (s DeleteContextResponse) GoString() string {
	return s.String()
}

func (s *DeleteContextResponse) GetHeaders() map[string]*string {
	return s.Headers
}

func (s *DeleteContextResponse) GetStatusCode() *int32 {
	return s.StatusCode
}

func (s *DeleteContextResponse) GetBody() *DeleteContextResponseBody {
	return s.Body
}

func (s *DeleteContextResponse) SetHeaders(v map[string]*string) *DeleteContextResponse {
	s.Headers = v
	return s
}

func (s *DeleteContextResponse) SetStatusCode(v int32) *DeleteContextResponse {
	s.StatusCode = &v
	return s
}

func (s *DeleteContextResponse) SetBody(v *DeleteContextResponseBody) *DeleteContextResponse {
	s.Body = v
	return s
}

func (s *DeleteContextResponse) Validate() error {
	return dara.Validate(s)
}
