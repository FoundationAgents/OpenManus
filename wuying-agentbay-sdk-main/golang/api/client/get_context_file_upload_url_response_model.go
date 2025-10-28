package client

import (
	"github.com/alibabacloud-go/tea/dara"
)

type iGetContextFileUploadUrlResponse interface {
	dara.Model
	String() string
	GoString() string
	SetHeaders(v map[string]*string) *GetContextFileUploadUrlResponse
	GetHeaders() map[string]*string
	SetStatusCode(v int32) *GetContextFileUploadUrlResponse
	GetStatusCode() *int32
	SetBody(v *GetContextFileUploadUrlResponseBody) *GetContextFileUploadUrlResponse
	GetBody() *GetContextFileUploadUrlResponseBody
}

type GetContextFileUploadUrlResponse struct {
	Headers    map[string]*string                   `json:"headers,omitempty" xml:"headers,omitempty"`
	StatusCode *int32                               `json:"statusCode,omitempty" xml:"statusCode,omitempty"`
	Body       *GetContextFileUploadUrlResponseBody `json:"body,omitempty" xml:"body,omitempty"`
}

func (s GetContextFileUploadUrlResponse) String() string {
	return dara.Prettify(s)
}

func (s GetContextFileUploadUrlResponse) GoString() string {
	return s.String()
}

func (s *GetContextFileUploadUrlResponse) GetHeaders() map[string]*string {
	return s.Headers
}

func (s *GetContextFileUploadUrlResponse) GetStatusCode() *int32 {
	return s.StatusCode
}

func (s *GetContextFileUploadUrlResponse) GetBody() *GetContextFileUploadUrlResponseBody {
	return s.Body
}

func (s *GetContextFileUploadUrlResponse) SetHeaders(v map[string]*string) *GetContextFileUploadUrlResponse {
	s.Headers = v
	return s
}

func (s *GetContextFileUploadUrlResponse) SetStatusCode(v int32) *GetContextFileUploadUrlResponse {
	s.StatusCode = &v
	return s
}

func (s *GetContextFileUploadUrlResponse) SetBody(v *GetContextFileUploadUrlResponseBody) *GetContextFileUploadUrlResponse {
	s.Body = v
	return s
}

func (s *GetContextFileUploadUrlResponse) Validate() error {
	return dara.Validate(s)
}
