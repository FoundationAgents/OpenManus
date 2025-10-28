package client

import (
	"github.com/alibabacloud-go/tea/dara"
)

type iGetContextFileUploadUrlRequest interface {
	dara.Model
	String() string
	GoString() string
	SetAuthorization(v string) *GetContextFileUploadUrlRequest
	GetAuthorization() *string
	SetContextId(v string) *GetContextFileUploadUrlRequest
	GetContextId() *string
	SetFilePath(v string) *GetContextFileUploadUrlRequest
	GetFilePath() *string
}

type GetContextFileUploadUrlRequest struct {
	Authorization *string `json:"Authorization,omitempty" xml:"Authorization,omitempty"`
	ContextId     *string `json:"ContextId,omitempty" xml:"ContextId,omitempty"`
	FilePath      *string `json:"FilePath,omitempty" xml:"FilePath,omitempty"`
}

func (s GetContextFileUploadUrlRequest) String() string {
	return dara.Prettify(s)
}

func (s GetContextFileUploadUrlRequest) GoString() string {
	return s.String()
}

func (s *GetContextFileUploadUrlRequest) GetAuthorization() *string {
	return s.Authorization
}

func (s *GetContextFileUploadUrlRequest) GetContextId() *string {
	return s.ContextId
}

func (s *GetContextFileUploadUrlRequest) GetFilePath() *string {
	return s.FilePath
}

func (s *GetContextFileUploadUrlRequest) SetAuthorization(v string) *GetContextFileUploadUrlRequest {
	s.Authorization = &v
	return s
}

func (s *GetContextFileUploadUrlRequest) SetContextId(v string) *GetContextFileUploadUrlRequest {
	s.ContextId = &v
	return s
}

func (s *GetContextFileUploadUrlRequest) SetFilePath(v string) *GetContextFileUploadUrlRequest {
	s.FilePath = &v
	return s
}

func (s *GetContextFileUploadUrlRequest) Validate() error {
	return dara.Validate(s)
}
