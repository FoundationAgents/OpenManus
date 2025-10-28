// This file is auto-generated, don't edit it. Thanks.
package client

import (
	"github.com/alibabacloud-go/tea/dara"
)

type iGetContextRequest interface {
	dara.Model
	String() string
	GoString() string
	SetAllowCreate(v bool) *GetContextRequest
	GetAllowCreate() *bool
	SetAuthorization(v string) *GetContextRequest
	GetAuthorization() *string
	SetName(v string) *GetContextRequest
	GetName() *string
}

type GetContextRequest struct {
	AllowCreate   *bool   `json:"AllowCreate,omitempty" xml:"AllowCreate,omitempty"`
	Authorization *string `json:"Authorization,omitempty" xml:"Authorization,omitempty"`
	Name          *string `json:"Name,omitempty" xml:"Name,omitempty"`
}

func (s GetContextRequest) String() string {
	return dara.Prettify(s)
}

func (s GetContextRequest) GoString() string {
	return s.String()
}

func (s *GetContextRequest) GetAllowCreate() *bool {
	return s.AllowCreate
}

func (s *GetContextRequest) GetAuthorization() *string {
	return s.Authorization
}

func (s *GetContextRequest) GetName() *string {
	return s.Name
}

func (s *GetContextRequest) SetAllowCreate(v bool) *GetContextRequest {
	s.AllowCreate = &v
	return s
}

func (s *GetContextRequest) SetAuthorization(v string) *GetContextRequest {
	s.Authorization = &v
	return s
}

func (s *GetContextRequest) SetName(v string) *GetContextRequest {
	s.Name = &v
	return s
}

func (s *GetContextRequest) Validate() error {
	return dara.Validate(s)
}
