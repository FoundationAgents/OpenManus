// This file is auto-generated, don't edit it. Thanks.
package client

import (
	"github.com/alibabacloud-go/tea/dara"
)

type iCallMcpToolRequest interface {
	dara.Model
	String() string
	GoString() string
	SetArgs(v string) *CallMcpToolRequest
	GetArgs() *string
	SetAuthorization(v string) *CallMcpToolRequest
	GetAuthorization() *string
	SetExternalUserId(v string) *CallMcpToolRequest
	GetExternalUserId() *string
	SetImageId(v string) *CallMcpToolRequest
	GetImageId() *string
	SetName(v string) *CallMcpToolRequest
	GetName() *string
	SetServer(v string) *CallMcpToolRequest
	GetServer() *string
	SetSessionId(v string) *CallMcpToolRequest
	GetSessionId() *string
	SetTool(v string) *CallMcpToolRequest
	GetTool() *string
}

type CallMcpToolRequest struct {
	Args           *string `json:"Args,omitempty" xml:"Args,omitempty"`
	Authorization  *string `json:"Authorization,omitempty" xml:"Authorization,omitempty"`
	ExternalUserId *string `json:"ExternalUserId,omitempty" xml:"ExternalUserId,omitempty"`
	ImageId        *string `json:"ImageId,omitempty" xml:"ImageId,omitempty"`
	Name           *string `json:"Name,omitempty" xml:"Name,omitempty"`
	Server         *string `json:"Server,omitempty" xml:"Server,omitempty"`
	SessionId      *string `json:"SessionId,omitempty" xml:"SessionId,omitempty"`
	Tool           *string `json:"Tool,omitempty" xml:"Tool,omitempty"`
}

func (s CallMcpToolRequest) String() string {
	return dara.Prettify(s)
}

func (s CallMcpToolRequest) GoString() string {
	return s.String()
}

func (s *CallMcpToolRequest) GetArgs() *string {
	return s.Args
}

func (s *CallMcpToolRequest) GetAuthorization() *string {
	return s.Authorization
}

func (s *CallMcpToolRequest) GetExternalUserId() *string {
	return s.ExternalUserId
}

func (s *CallMcpToolRequest) GetImageId() *string {
	return s.ImageId
}

func (s *CallMcpToolRequest) GetName() *string {
	return s.Name
}

func (s *CallMcpToolRequest) GetServer() *string {
	return s.Server
}

func (s *CallMcpToolRequest) GetSessionId() *string {
	return s.SessionId
}

func (s *CallMcpToolRequest) GetTool() *string {
	return s.Tool
}

func (s *CallMcpToolRequest) SetArgs(v string) *CallMcpToolRequest {
	s.Args = &v
	return s
}

func (s *CallMcpToolRequest) SetAuthorization(v string) *CallMcpToolRequest {
	s.Authorization = &v
	return s
}

func (s *CallMcpToolRequest) SetExternalUserId(v string) *CallMcpToolRequest {
	s.ExternalUserId = &v
	return s
}

func (s *CallMcpToolRequest) SetImageId(v string) *CallMcpToolRequest {
	s.ImageId = &v
	return s
}

func (s *CallMcpToolRequest) SetName(v string) *CallMcpToolRequest {
	s.Name = &v
	return s
}

func (s *CallMcpToolRequest) SetServer(v string) *CallMcpToolRequest {
	s.Server = &v
	return s
}

func (s *CallMcpToolRequest) SetSessionId(v string) *CallMcpToolRequest {
	s.SessionId = &v
	return s
}

func (s *CallMcpToolRequest) SetTool(v string) *CallMcpToolRequest {
	s.Tool = &v
	return s
}

func (s *CallMcpToolRequest) Validate() error {
	return dara.Validate(s)
}
