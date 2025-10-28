// This file is auto-generated, don't edit it. Thanks.
package client

import (
	"github.com/alibabacloud-go/tea/dara"
)

type iListContextsRequest interface {
	dara.Model
	String() string
	GoString() string
	SetAuthorization(v string) *ListContextsRequest
	GetAuthorization() *string
	SetMaxResults(v int32) *ListContextsRequest
	GetMaxResults() *int32
	SetNextToken(v string) *ListContextsRequest
	GetNextToken() *string
}

type ListContextsRequest struct {
	Authorization *string `json:"Authorization,omitempty" xml:"Authorization,omitempty"`
	MaxResults    *int32  `json:"MaxResults,omitempty" xml:"MaxResults,omitempty"`
	NextToken     *string `json:"NextToken,omitempty" xml:"NextToken,omitempty"`
}

func (s ListContextsRequest) String() string {
	return dara.Prettify(s)
}

func (s ListContextsRequest) GoString() string {
	return s.String()
}

func (s *ListContextsRequest) GetAuthorization() *string {
	return s.Authorization
}

func (s *ListContextsRequest) GetMaxResults() *int32 {
	return s.MaxResults
}

func (s *ListContextsRequest) GetNextToken() *string {
	return s.NextToken
}

func (s *ListContextsRequest) SetAuthorization(v string) *ListContextsRequest {
	s.Authorization = &v
	return s
}

func (s *ListContextsRequest) SetMaxResults(v int32) *ListContextsRequest {
	s.MaxResults = &v
	return s
}

func (s *ListContextsRequest) SetNextToken(v string) *ListContextsRequest {
	s.NextToken = &v
	return s
}

func (s *ListContextsRequest) Validate() error {
	return dara.Validate(s)
}
