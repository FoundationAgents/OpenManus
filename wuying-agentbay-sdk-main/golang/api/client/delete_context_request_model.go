// This file is auto-generated, don't edit it. Thanks.
package client

import (
	"github.com/alibabacloud-go/tea/dara"
)

type iDeleteContextRequest interface {
	dara.Model
	String() string
	GoString() string
	SetAuthorization(v string) *DeleteContextRequest
	GetAuthorization() *string
	SetId(v string) *DeleteContextRequest
	GetId() *string
}

type DeleteContextRequest struct {
	Authorization *string `json:"Authorization,omitempty" xml:"Authorization,omitempty"`
	Id            *string `json:"Id,omitempty" xml:"Id,omitempty"`
}

func (s DeleteContextRequest) String() string {
	return dara.Prettify(s)
}

func (s DeleteContextRequest) GoString() string {
	return s.String()
}

func (s *DeleteContextRequest) GetAuthorization() *string {
	return s.Authorization
}

func (s *DeleteContextRequest) GetId() *string {
	return s.Id
}

func (s *DeleteContextRequest) SetAuthorization(v string) *DeleteContextRequest {
	s.Authorization = &v
	return s
}

func (s *DeleteContextRequest) SetId(v string) *DeleteContextRequest {
	s.Id = &v
	return s
}

func (s *DeleteContextRequest) Validate() error {
	return dara.Validate(s)
}
