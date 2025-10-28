package client

import (
	"github.com/alibabacloud-go/tea/dara"
)

type iDescribeContextFilesResponse interface {
	dara.Model
	String() string
	GoString() string
	SetHeaders(v map[string]*string) *DescribeContextFilesResponse
	GetHeaders() map[string]*string
	SetStatusCode(v int32) *DescribeContextFilesResponse
	GetStatusCode() *int32
	SetBody(v *DescribeContextFilesResponseBody) *DescribeContextFilesResponse
	GetBody() *DescribeContextFilesResponseBody
}

type DescribeContextFilesResponse struct {
	Headers    map[string]*string                `json:"headers,omitempty" xml:"headers,omitempty"`
	StatusCode *int32                            `json:"statusCode,omitempty" xml:"statusCode,omitempty"`
	Body       *DescribeContextFilesResponseBody `json:"body,omitempty" xml:"body,omitempty"`
}

func (s DescribeContextFilesResponse) String() string {
	return dara.Prettify(s)
}

func (s DescribeContextFilesResponse) GoString() string {
	return s.String()
}

func (s *DescribeContextFilesResponse) GetHeaders() map[string]*string {
	return s.Headers
}

func (s *DescribeContextFilesResponse) GetStatusCode() *int32 {
	return s.StatusCode
}

func (s *DescribeContextFilesResponse) GetBody() *DescribeContextFilesResponseBody {
	return s.Body
}

func (s *DescribeContextFilesResponse) SetHeaders(v map[string]*string) *DescribeContextFilesResponse {
	s.Headers = v
	return s
}

func (s *DescribeContextFilesResponse) SetStatusCode(v int32) *DescribeContextFilesResponse {
	s.StatusCode = &v
	return s
}

func (s *DescribeContextFilesResponse) SetBody(v *DescribeContextFilesResponseBody) *DescribeContextFilesResponse {
	s.Body = v
	return s
}

func (s *DescribeContextFilesResponse) Validate() error {
	return dara.Validate(s)
}
