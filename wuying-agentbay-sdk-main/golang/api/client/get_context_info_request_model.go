// This file is auto-generated, don't edit it. Thanks.
package client

import (
	"github.com/alibabacloud-go/tea/dara"
)

type iGetContextInfoRequest interface {
	dara.Model
	String() string
	GoString() string
	SetAuthorization(v string) *GetContextInfoRequest
	GetAuthorization() *string
	SetContextId(v string) *GetContextInfoRequest
	GetContextId() *string
	SetPath(v string) *GetContextInfoRequest
	GetPath() *string
	SetSessionId(v string) *GetContextInfoRequest
	GetSessionId() *string
	SetTaskType(v string) *GetContextInfoRequest
	GetTaskType() *string
}

type GetContextInfoRequest struct {
	Authorization *string `json:"Authorization,omitempty" xml:"Authorization,omitempty"`
	ContextId     *string `json:"ContextId,omitempty" xml:"ContextId,omitempty"`
	Path          *string `json:"Path,omitempty" xml:"Path,omitempty"`
	SessionId     *string `json:"SessionId,omitempty" xml:"SessionId,omitempty"`
	TaskType      *string `json:"TaskType,omitempty" xml:"TaskType,omitempty"`
}

func (s GetContextInfoRequest) String() string {
	return dara.Prettify(s)
}

func (s GetContextInfoRequest) GoString() string {
	return s.String()
}

func (s *GetContextInfoRequest) GetAuthorization() *string {
	return s.Authorization
}

func (s *GetContextInfoRequest) GetContextId() *string {
	return s.ContextId
}

func (s *GetContextInfoRequest) GetPath() *string {
	return s.Path
}

func (s *GetContextInfoRequest) GetSessionId() *string {
	return s.SessionId
}

func (s *GetContextInfoRequest) GetTaskType() *string {
	return s.TaskType
}

func (s *GetContextInfoRequest) SetAuthorization(v string) *GetContextInfoRequest {
	s.Authorization = &v
	return s
}

func (s *GetContextInfoRequest) SetContextId(v string) *GetContextInfoRequest {
	s.ContextId = &v
	return s
}

func (s *GetContextInfoRequest) SetPath(v string) *GetContextInfoRequest {
	s.Path = &v
	return s
}

func (s *GetContextInfoRequest) SetSessionId(v string) *GetContextInfoRequest {
	s.SessionId = &v
	return s
}

func (s *GetContextInfoRequest) SetTaskType(v string) *GetContextInfoRequest {
	s.TaskType = &v
	return s
}

func (s *GetContextInfoRequest) Validate() error {
	return dara.Validate(s)
}
