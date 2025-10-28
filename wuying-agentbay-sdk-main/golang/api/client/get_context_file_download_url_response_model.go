package client

import (
	"github.com/alibabacloud-go/tea/dara"
)

type iGetContextFileDownloadUrlResponse interface {
	dara.Model
	String() string
	GoString() string
	SetHeaders(v map[string]*string) *GetContextFileDownloadUrlResponse
	GetHeaders() map[string]*string
	SetStatusCode(v int32) *GetContextFileDownloadUrlResponse
	GetStatusCode() *int32
	SetBody(v *GetContextFileDownloadUrlResponseBody) *GetContextFileDownloadUrlResponse
	GetBody() *GetContextFileDownloadUrlResponseBody
}

type GetContextFileDownloadUrlResponse struct {
	Headers    map[string]*string                     `json:"headers,omitempty" xml:"headers,omitempty"`
	StatusCode *int32                                 `json:"statusCode,omitempty" xml:"statusCode,omitempty"`
	Body       *GetContextFileDownloadUrlResponseBody `json:"body,omitempty" xml:"body,omitempty"`
}

func (s GetContextFileDownloadUrlResponse) String() string {
	return dara.Prettify(s)
}

func (s GetContextFileDownloadUrlResponse) GoString() string {
	return s.String()
}

func (s *GetContextFileDownloadUrlResponse) GetHeaders() map[string]*string {
	return s.Headers
}

func (s *GetContextFileDownloadUrlResponse) GetStatusCode() *int32 {
	return s.StatusCode
}

func (s *GetContextFileDownloadUrlResponse) GetBody() *GetContextFileDownloadUrlResponseBody {
	return s.Body
}

func (s *GetContextFileDownloadUrlResponse) SetHeaders(v map[string]*string) *GetContextFileDownloadUrlResponse {
	s.Headers = v
	return s
}

func (s *GetContextFileDownloadUrlResponse) SetStatusCode(v int32) *GetContextFileDownloadUrlResponse {
	s.StatusCode = &v
	return s
}

func (s *GetContextFileDownloadUrlResponse) SetBody(v *GetContextFileDownloadUrlResponseBody) *GetContextFileDownloadUrlResponse {
	s.Body = v
	return s
}

func (s *GetContextFileDownloadUrlResponse) Validate() error {
	return dara.Validate(s)
}
