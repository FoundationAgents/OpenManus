package client

import (
	"github.com/alibabacloud-go/tea/dara"
)

type iGetContextFileDownloadUrlRequest interface {
	dara.Model
	String() string
	GoString() string
	SetAuthorization(v string) *GetContextFileDownloadUrlRequest
	GetAuthorization() *string
	SetContextId(v string) *GetContextFileDownloadUrlRequest
	GetContextId() *string
	SetFilePath(v string) *GetContextFileDownloadUrlRequest
	GetFilePath() *string
}

type GetContextFileDownloadUrlRequest struct {
	Authorization *string `json:"Authorization,omitempty" xml:"Authorization,omitempty"`
	ContextId     *string `json:"ContextId,omitempty" xml:"ContextId,omitempty"`
	FilePath      *string `json:"FilePath,omitempty" xml:"FilePath,omitempty"`
}

func (s GetContextFileDownloadUrlRequest) String() string {
	return dara.Prettify(s)
}

func (s GetContextFileDownloadUrlRequest) GoString() string {
	return s.String()
}

func (s *GetContextFileDownloadUrlRequest) GetAuthorization() *string {
	return s.Authorization
}

func (s *GetContextFileDownloadUrlRequest) GetContextId() *string {
	return s.ContextId
}

func (s *GetContextFileDownloadUrlRequest) GetFilePath() *string {
	return s.FilePath
}

func (s *GetContextFileDownloadUrlRequest) SetAuthorization(v string) *GetContextFileDownloadUrlRequest {
	s.Authorization = &v
	return s
}

func (s *GetContextFileDownloadUrlRequest) SetContextId(v string) *GetContextFileDownloadUrlRequest {
	s.ContextId = &v
	return s
}

func (s *GetContextFileDownloadUrlRequest) SetFilePath(v string) *GetContextFileDownloadUrlRequest {
	s.FilePath = &v
	return s
}

func (s *GetContextFileDownloadUrlRequest) Validate() error {
	return dara.Validate(s)
}
