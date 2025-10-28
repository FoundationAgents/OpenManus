package client

import (
	"github.com/alibabacloud-go/tea/dara"
)

type iDeleteContextFileRequest interface {
	dara.Model
	String() string
	GoString() string
	SetAuthorization(v string) *DeleteContextFileRequest
	GetAuthorization() *string
	SetContextId(v string) *DeleteContextFileRequest
	GetContextId() *string
	SetFilePath(v string) *DeleteContextFileRequest
	GetFilePath() *string
}

type DeleteContextFileRequest struct {
	Authorization *string `json:"Authorization,omitempty" xml:"Authorization,omitempty"`
	ContextId     *string `json:"ContextId,omitempty" xml:"ContextId,omitempty"`
	FilePath      *string `json:"FilePath,omitempty" xml:"FilePath,omitempty"`
}

func (s DeleteContextFileRequest) String() string {
	return dara.Prettify(s)
}

func (s DeleteContextFileRequest) GoString() string {
	return s.String()
}

func (s *DeleteContextFileRequest) GetAuthorization() *string {
	return s.Authorization
}

func (s *DeleteContextFileRequest) GetContextId() *string {
	return s.ContextId
}

func (s *DeleteContextFileRequest) GetFilePath() *string {
	return s.FilePath
}

func (s *DeleteContextFileRequest) SetAuthorization(v string) *DeleteContextFileRequest {
	s.Authorization = &v
	return s
}

func (s *DeleteContextFileRequest) SetContextId(v string) *DeleteContextFileRequest {
	s.ContextId = &v
	return s
}

func (s *DeleteContextFileRequest) SetFilePath(v string) *DeleteContextFileRequest {
	s.FilePath = &v
	return s
}

func (s *DeleteContextFileRequest) Validate() error {
	return dara.Validate(s)
}
