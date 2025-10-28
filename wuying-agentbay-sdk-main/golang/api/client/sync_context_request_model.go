// This file is auto-generated, don't edit it. Thanks.
package client

import (
	"github.com/alibabacloud-go/tea/dara"
)

type iSyncContextRequest interface {
	dara.Model
	String() string
	GoString() string
	SetAuthorization(v string) *SyncContextRequest
	GetAuthorization() *string
	SetContextId(v string) *SyncContextRequest
	GetContextId() *string
	SetMode(v string) *SyncContextRequest
	GetMode() *string
	SetPath(v string) *SyncContextRequest
	GetPath() *string
	SetSessionId(v string) *SyncContextRequest
	GetSessionId() *string
}

type SyncContextRequest struct {
	Authorization *string `json:"Authorization,omitempty" xml:"Authorization,omitempty"`
	ContextId     *string `json:"ContextId,omitempty" xml:"ContextId,omitempty"`
	Mode          *string `json:"Mode,omitempty" xml:"Mode,omitempty"`
	Path          *string `json:"Path,omitempty" xml:"Path,omitempty"`
	SessionId     *string `json:"SessionId,omitempty" xml:"SessionId,omitempty"`
}

func (s SyncContextRequest) String() string {
	return dara.Prettify(s)
}

func (s SyncContextRequest) GoString() string {
	return s.String()
}

func (s *SyncContextRequest) GetAuthorization() *string {
	return s.Authorization
}

func (s *SyncContextRequest) GetContextId() *string {
	return s.ContextId
}

func (s *SyncContextRequest) GetMode() *string {
	return s.Mode
}

func (s *SyncContextRequest) GetPath() *string {
	return s.Path
}

func (s *SyncContextRequest) GetSessionId() *string {
	return s.SessionId
}

func (s *SyncContextRequest) SetAuthorization(v string) *SyncContextRequest {
	s.Authorization = &v
	return s
}

func (s *SyncContextRequest) SetContextId(v string) *SyncContextRequest {
	s.ContextId = &v
	return s
}

func (s *SyncContextRequest) SetMode(v string) *SyncContextRequest {
	s.Mode = &v
	return s
}

func (s *SyncContextRequest) SetPath(v string) *SyncContextRequest {
	s.Path = &v
	return s
}

func (s *SyncContextRequest) SetSessionId(v string) *SyncContextRequest {
	s.SessionId = &v
	return s
}

func (s *SyncContextRequest) Validate() error {
	return dara.Validate(s)
}
