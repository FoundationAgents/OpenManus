// This file is auto-generated, don't edit it. Thanks.
package client

import (
	"github.com/alibabacloud-go/tea/dara"
)

type iCreateMcpSessionShrinkRequest interface {
	dara.Model
	String() string
	GoString() string
	SetAuthorization(v string) *CreateMcpSessionShrinkRequest
	GetAuthorization() *string
	SetContextId(v string) *CreateMcpSessionShrinkRequest
	GetContextId() *string
	SetExternalUserId(v string) *CreateMcpSessionShrinkRequest
	GetExternalUserId() *string
	SetImageId(v string) *CreateMcpSessionShrinkRequest
	GetImageId() *string
	SetLabels(v string) *CreateMcpSessionShrinkRequest
	GetLabels() *string
	SetMcpPolicyId(v string) *CreateMcpSessionShrinkRequest
	GetMcpPolicyId() *string
	SetPersistenceDataListShrink(v string) *CreateMcpSessionShrinkRequest
	GetPersistenceDataListShrink() *string
	SetSessionId(v string) *CreateMcpSessionShrinkRequest
	GetSessionId() *string
	SetVpcResource(v bool) *CreateMcpSessionShrinkRequest
	GetVpcResource() *bool
}

type CreateMcpSessionShrinkRequest struct {
	Authorization             *string `json:"Authorization,omitempty" xml:"Authorization,omitempty"`
	ContextId                 *string `json:"ContextId,omitempty" xml:"ContextId,omitempty"`
	ExternalUserId            *string `json:"ExternalUserId,omitempty" xml:"ExternalUserId,omitempty"`
	ImageId                   *string `json:"ImageId,omitempty" xml:"ImageId,omitempty"`
	Labels                    *string `json:"Labels,omitempty" xml:"Labels,omitempty"`
	McpPolicyId               *string `json:"McpPolicyId,omitempty" xml:"McpPolicyId,omitempty"`
	PersistenceDataListShrink *string `json:"PersistenceDataList,omitempty" xml:"PersistenceDataList,omitempty"`
	SessionId                 *string `json:"SessionId,omitempty" xml:"SessionId,omitempty"`
	VpcResource               *bool   `json:"VpcResource,omitempty" xml:"VpcResource,omitempty"`
}

func (s CreateMcpSessionShrinkRequest) String() string {
	return dara.Prettify(s)
}

func (s CreateMcpSessionShrinkRequest) GoString() string {
	return s.String()
}

func (s *CreateMcpSessionShrinkRequest) GetAuthorization() *string {
	return s.Authorization
}

func (s *CreateMcpSessionShrinkRequest) GetContextId() *string {
	return s.ContextId
}

func (s *CreateMcpSessionShrinkRequest) GetExternalUserId() *string {
	return s.ExternalUserId
}

func (s *CreateMcpSessionShrinkRequest) GetImageId() *string {
	return s.ImageId
}

func (s *CreateMcpSessionShrinkRequest) GetLabels() *string {
	return s.Labels
}

func (s *CreateMcpSessionShrinkRequest) GetMcpPolicyId() *string {
	return s.McpPolicyId
}

func (s *CreateMcpSessionShrinkRequest) GetPersistenceDataListShrink() *string {
	return s.PersistenceDataListShrink
}

func (s *CreateMcpSessionShrinkRequest) GetSessionId() *string {
	return s.SessionId
}

func (s *CreateMcpSessionShrinkRequest) GetVpcResource() *bool {
	return s.VpcResource
}

func (s *CreateMcpSessionShrinkRequest) SetAuthorization(v string) *CreateMcpSessionShrinkRequest {
	s.Authorization = &v
	return s
}

func (s *CreateMcpSessionShrinkRequest) SetContextId(v string) *CreateMcpSessionShrinkRequest {
	s.ContextId = &v
	return s
}

func (s *CreateMcpSessionShrinkRequest) SetExternalUserId(v string) *CreateMcpSessionShrinkRequest {
	s.ExternalUserId = &v
	return s
}

func (s *CreateMcpSessionShrinkRequest) SetImageId(v string) *CreateMcpSessionShrinkRequest {
	s.ImageId = &v
	return s
}

func (s *CreateMcpSessionShrinkRequest) SetLabels(v string) *CreateMcpSessionShrinkRequest {
	s.Labels = &v
	return s
}

func (s *CreateMcpSessionShrinkRequest) SetMcpPolicyId(v string) *CreateMcpSessionShrinkRequest {
	s.McpPolicyId = &v
	return s
}

func (s *CreateMcpSessionShrinkRequest) SetPersistenceDataListShrink(v string) *CreateMcpSessionShrinkRequest {
	s.PersistenceDataListShrink = &v
	return s
}

func (s *CreateMcpSessionShrinkRequest) SetSessionId(v string) *CreateMcpSessionShrinkRequest {
	s.SessionId = &v
	return s
}

func (s *CreateMcpSessionShrinkRequest) SetVpcResource(v bool) *CreateMcpSessionShrinkRequest {
	s.VpcResource = &v
	return s
}

func (s *CreateMcpSessionShrinkRequest) Validate() error {
	return dara.Validate(s)
}
