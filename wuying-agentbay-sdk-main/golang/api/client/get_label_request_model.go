// This file is auto-generated, don't edit it. Thanks.
package client

import (
	"github.com/alibabacloud-go/tea/dara"
)

type iGetLabelRequest interface {
	dara.Model
	String() string
	GoString() string
	SetAuthorization(v string) *GetLabelRequest
	GetAuthorization() *string
	SetMaxResults(v int32) *GetLabelRequest
	GetMaxResults() *int32
	SetNextToken(v string) *GetLabelRequest
	GetNextToken() *string
	SetSessionId(v string) *GetLabelRequest
	GetSessionId() *string
}

type GetLabelRequest struct {
	Authorization *string `json:"Authorization,omitempty" xml:"Authorization,omitempty"`
	MaxResults    *int32  `json:"MaxResults,omitempty" xml:"MaxResults,omitempty"`
	NextToken     *string `json:"NextToken,omitempty" xml:"NextToken,omitempty"`
	SessionId     *string `json:"SessionId,omitempty" xml:"SessionId,omitempty"`
}

func (s GetLabelRequest) String() string {
	return dara.Prettify(s)
}

func (s GetLabelRequest) GoString() string {
	return s.String()
}

func (s *GetLabelRequest) GetAuthorization() *string {
	return s.Authorization
}

func (s *GetLabelRequest) GetMaxResults() *int32 {
	return s.MaxResults
}

func (s *GetLabelRequest) GetNextToken() *string {
	return s.NextToken
}

func (s *GetLabelRequest) GetSessionId() *string {
	return s.SessionId
}

func (s *GetLabelRequest) SetAuthorization(v string) *GetLabelRequest {
	s.Authorization = &v
	return s
}

func (s *GetLabelRequest) SetMaxResults(v int32) *GetLabelRequest {
	s.MaxResults = &v
	return s
}

func (s *GetLabelRequest) SetNextToken(v string) *GetLabelRequest {
	s.NextToken = &v
	return s
}

func (s *GetLabelRequest) SetSessionId(v string) *GetLabelRequest {
	s.SessionId = &v
	return s
}

func (s *GetLabelRequest) Validate() error {
	return dara.Validate(s)
}
