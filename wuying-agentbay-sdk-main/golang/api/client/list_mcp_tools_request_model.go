// This file is auto-generated, don't edit it. Thanks.
package client

import (
	"github.com/alibabacloud-go/tea/dara"
)

type iListMcpToolsRequest interface {
	dara.Model
	String() string
	GoString() string
	SetAuthorization(v string) *ListMcpToolsRequest
	GetAuthorization() *string
	SetImageId(v string) *ListMcpToolsRequest
	GetImageId() *string
}

type ListMcpToolsRequest struct {
	Authorization *string `json:"Authorization,omitempty" xml:"Authorization,omitempty"`
	ImageId       *string `json:"ImageId,omitempty" xml:"ImageId,omitempty"`
}

func (s ListMcpToolsRequest) String() string {
	return dara.Prettify(s)
}

func (s ListMcpToolsRequest) GoString() string {
	return s.String()
}

func (s *ListMcpToolsRequest) GetAuthorization() *string {
	return s.Authorization
}

func (s *ListMcpToolsRequest) GetImageId() *string {
	return s.ImageId
}

func (s *ListMcpToolsRequest) SetAuthorization(v string) *ListMcpToolsRequest {
	s.Authorization = &v
	return s
}

func (s *ListMcpToolsRequest) SetImageId(v string) *ListMcpToolsRequest {
	s.ImageId = &v
	return s
}

func (s *ListMcpToolsRequest) Validate() error {
	return dara.Validate(s)
}
