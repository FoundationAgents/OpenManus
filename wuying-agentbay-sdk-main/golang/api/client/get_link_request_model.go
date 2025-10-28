// This file is auto-generated, don't edit it. Thanks.
package client

import (
	"github.com/alibabacloud-go/tea/dara"
)

type iGetLinkRequest interface {
	dara.Model
	String() string
	GoString() string
	SetAuthorization(v string) *GetLinkRequest
	GetAuthorization() *string
	SetPort(v int32) *GetLinkRequest
	GetPort() *int32
	SetProtocolType(v string) *GetLinkRequest
	GetProtocolType() *string
	SetSessionId(v string) *GetLinkRequest
	GetSessionId() *string
}

type GetLinkRequest struct {
	Authorization *string `json:"Authorization,omitempty" xml:"Authorization,omitempty"`
	Port          *int32  `json:"Port,omitempty" xml:"Port,omitempty"`
	ProtocolType  *string `json:"ProtocolType,omitempty" xml:"ProtocolType,omitempty"`
	SessionId     *string `json:"SessionId,omitempty" xml:"SessionId,omitempty"`
}

func (s GetLinkRequest) String() string {
	return dara.Prettify(s)
}

func (s GetLinkRequest) GoString() string {
	return s.String()
}

func (s *GetLinkRequest) GetAuthorization() *string {
	return s.Authorization
}

func (s *GetLinkRequest) GetPort() *int32 {
	return s.Port
}

func (s *GetLinkRequest) GetProtocolType() *string {
	return s.ProtocolType
}

func (s *GetLinkRequest) GetSessionId() *string {
	return s.SessionId
}

func (s *GetLinkRequest) SetAuthorization(v string) *GetLinkRequest {
	s.Authorization = &v
	return s
}

func (s *GetLinkRequest) SetPort(v int32) *GetLinkRequest {
	s.Port = &v
	return s
}

func (s *GetLinkRequest) SetProtocolType(v string) *GetLinkRequest {
	s.ProtocolType = &v
	return s
}

func (s *GetLinkRequest) SetSessionId(v string) *GetLinkRequest {
	s.SessionId = &v
	return s
}

func (s *GetLinkRequest) Validate() error {
	return dara.Validate(s)
}
