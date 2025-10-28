// This file is auto-generated, don't edit it. Thanks.
package client

import (
	"github.com/alibabacloud-go/tea/dara"
)

type iReleaseMcpSessionRequest interface {
	dara.Model
	String() string
	GoString() string
	SetAuthorization(v string) *ReleaseMcpSessionRequest
	GetAuthorization() *string
	SetSessionId(v string) *ReleaseMcpSessionRequest
	GetSessionId() *string
}

type ReleaseMcpSessionRequest struct {
	Authorization *string `json:"Authorization,omitempty" xml:"Authorization,omitempty"`
	SessionId     *string `json:"SessionId,omitempty" xml:"SessionId,omitempty"`
}

func (s ReleaseMcpSessionRequest) String() string {
	return dara.Prettify(s)
}

func (s ReleaseMcpSessionRequest) GoString() string {
	return s.String()
}

func (s *ReleaseMcpSessionRequest) GetAuthorization() *string {
	return s.Authorization
}

func (s *ReleaseMcpSessionRequest) GetSessionId() *string {
	return s.SessionId
}

func (s *ReleaseMcpSessionRequest) SetAuthorization(v string) *ReleaseMcpSessionRequest {
	s.Authorization = &v
	return s
}

func (s *ReleaseMcpSessionRequest) SetSessionId(v string) *ReleaseMcpSessionRequest {
	s.SessionId = &v
	return s
}

func (s *ReleaseMcpSessionRequest) Validate() error {
	return dara.Validate(s)
}
