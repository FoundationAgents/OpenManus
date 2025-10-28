// This file is auto-generated, don't edit it. Thanks.
package client

import (
	"github.com/alibabacloud-go/tea/dara"
)

type iGetMcpResourceRequest interface {
	dara.Model
	String() string
	GoString() string
	SetAuthorization(v string) *GetMcpResourceRequest
	GetAuthorization() *string
	SetSessionId(v string) *GetMcpResourceRequest
	GetSessionId() *string
}

type GetMcpResourceRequest struct {
	Authorization *string `json:"Authorization,omitempty" xml:"Authorization,omitempty"`
	SessionId     *string `json:"SessionId,omitempty" xml:"SessionId,omitempty"`
}

func (s GetMcpResourceRequest) String() string {
	return dara.Prettify(s)
}

func (s GetMcpResourceRequest) GoString() string {
	return s.String()
}

func (s *GetMcpResourceRequest) GetAuthorization() *string {
	return s.Authorization
}

func (s *GetMcpResourceRequest) GetSessionId() *string {
	return s.SessionId
}

func (s *GetMcpResourceRequest) SetAuthorization(v string) *GetMcpResourceRequest {
	s.Authorization = &v
	return s
}

func (s *GetMcpResourceRequest) SetSessionId(v string) *GetMcpResourceRequest {
	s.SessionId = &v
	return s
}

func (s *GetMcpResourceRequest) Validate() error {
	return dara.Validate(s)
}
