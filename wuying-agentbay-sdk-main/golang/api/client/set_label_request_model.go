// This file is auto-generated, don't edit it. Thanks.
package client

import (
	"github.com/alibabacloud-go/tea/dara"
)

type iSetLabelRequest interface {
	dara.Model
	String() string
	GoString() string
	SetAuthorization(v string) *SetLabelRequest
	GetAuthorization() *string
	SetLabels(v string) *SetLabelRequest
	GetLabels() *string
	SetSessionId(v string) *SetLabelRequest
	GetSessionId() *string
}

type SetLabelRequest struct {
	Authorization *string `json:"Authorization,omitempty" xml:"Authorization,omitempty"`
	Labels        *string `json:"Labels,omitempty" xml:"Labels,omitempty"`
	SessionId     *string `json:"SessionId,omitempty" xml:"SessionId,omitempty"`
}

func (s SetLabelRequest) String() string {
	return dara.Prettify(s)
}

func (s SetLabelRequest) GoString() string {
	return s.String()
}

func (s *SetLabelRequest) GetAuthorization() *string {
	return s.Authorization
}

func (s *SetLabelRequest) GetLabels() *string {
	return s.Labels
}

func (s *SetLabelRequest) GetSessionId() *string {
	return s.SessionId
}

func (s *SetLabelRequest) SetAuthorization(v string) *SetLabelRequest {
	s.Authorization = &v
	return s
}

func (s *SetLabelRequest) SetLabels(v string) *SetLabelRequest {
	s.Labels = &v
	return s
}

func (s *SetLabelRequest) SetSessionId(v string) *SetLabelRequest {
	s.SessionId = &v
	return s
}

func (s *SetLabelRequest) Validate() error {
	return dara.Validate(s)
}
