// This file is auto-generated, don't edit it. Thanks.
package client

import (
	"github.com/alibabacloud-go/tea/dara"
)

type iGetSessionRequest interface {
	dara.Model
	String() string
	GoString() string
	SetAuthorization(v string) *GetSessionRequest
	GetAuthorization() *string
	SetSessionId(v string) *GetSessionRequest
	GetSessionId() *string
}

type GetSessionRequest struct {
	Authorization *string `json:"Authorization,omitempty" xml:"Authorization,omitempty"`
	SessionId     *string `json:"SessionId,omitempty" xml:"SessionId,omitempty"`
}

func (s GetSessionRequest) String() string {
	return dara.Prettify(s)
}

func (s GetSessionRequest) GoString() string {
	return s.String()
}

func (s *GetSessionRequest) GetAuthorization() *string {
	return s.Authorization
}

func (s *GetSessionRequest) GetSessionId() *string {
	return s.SessionId
}

func (s *GetSessionRequest) SetAuthorization(v string) *GetSessionRequest {
	s.Authorization = &v
	return s
}

func (s *GetSessionRequest) SetSessionId(v string) *GetSessionRequest {
	s.SessionId = &v
	return s
}

func (s *GetSessionRequest) Validate() error {
	return dara.Validate(s)
}
