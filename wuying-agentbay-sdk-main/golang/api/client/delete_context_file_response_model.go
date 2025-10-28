package client

import (
	"github.com/alibabacloud-go/tea/dara"
)

type iDeleteContextFileResponse interface {
	dara.Model
	String() string
	GoString() string
	SetHeaders(v map[string]*string) *DeleteContextFileResponse
	GetHeaders() map[string]*string
	SetStatusCode(v int32) *DeleteContextFileResponse
	GetStatusCode() *int32
	SetBody(v *DeleteContextFileResponseBody) *DeleteContextFileResponse
	GetBody() *DeleteContextFileResponseBody
}

type DeleteContextFileResponse struct {
	Headers    map[string]*string             `json:"headers,omitempty" xml:"headers,omitempty"`
	StatusCode *int32                         `json:"statusCode,omitempty" xml:"statusCode,omitempty"`
	Body       *DeleteContextFileResponseBody `json:"body,omitempty" xml:"body,omitempty"`
}

func (s DeleteContextFileResponse) String() string {
	return dara.Prettify(s)
}

func (s DeleteContextFileResponse) GoString() string {
	return s.String()
}

func (s *DeleteContextFileResponse) GetHeaders() map[string]*string {
	return s.Headers
}

func (s *DeleteContextFileResponse) GetStatusCode() *int32 {
	return s.StatusCode
}

func (s *DeleteContextFileResponse) GetBody() *DeleteContextFileResponseBody {
	return s.Body
}

func (s *DeleteContextFileResponse) SetHeaders(v map[string]*string) *DeleteContextFileResponse {
	s.Headers = v
	return s
}

func (s *DeleteContextFileResponse) SetStatusCode(v int32) *DeleteContextFileResponse {
	s.StatusCode = &v
	return s
}

func (s *DeleteContextFileResponse) SetBody(v *DeleteContextFileResponseBody) *DeleteContextFileResponse {
	s.Body = v
	return s
}

func (s *DeleteContextFileResponse) Validate() error {
	return dara.Validate(s)
}
