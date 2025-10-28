// This file is auto-generated, don't edit it. Thanks.
package client

import (
	"github.com/alibabacloud-go/tea/dara"
)

type iModifyContextRequest interface {
	dara.Model
	String() string
	GoString() string
	SetAuthorization(v string) *ModifyContextRequest
	GetAuthorization() *string
	SetId(v string) *ModifyContextRequest
	GetId() *string
	SetName(v string) *ModifyContextRequest
	GetName() *string
}

type ModifyContextRequest struct {
	Authorization *string `json:"Authorization,omitempty" xml:"Authorization,omitempty"`
	Id            *string `json:"Id,omitempty" xml:"Id,omitempty"`
	Name          *string `json:"Name,omitempty" xml:"Name,omitempty"`
}

func (s ModifyContextRequest) String() string {
	return dara.Prettify(s)
}

func (s ModifyContextRequest) GoString() string {
	return s.String()
}

func (s *ModifyContextRequest) GetAuthorization() *string {
	return s.Authorization
}

func (s *ModifyContextRequest) GetId() *string {
	return s.Id
}

func (s *ModifyContextRequest) GetName() *string {
	return s.Name
}

func (s *ModifyContextRequest) SetAuthorization(v string) *ModifyContextRequest {
	s.Authorization = &v
	return s
}

func (s *ModifyContextRequest) SetId(v string) *ModifyContextRequest {
	s.Id = &v
	return s
}

func (s *ModifyContextRequest) SetName(v string) *ModifyContextRequest {
	s.Name = &v
	return s
}

func (s *ModifyContextRequest) Validate() error {
	return dara.Validate(s)
}
