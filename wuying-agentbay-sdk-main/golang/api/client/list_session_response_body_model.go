// This file is auto-generated, don't edit it. Thanks.
package client

import (
	"github.com/alibabacloud-go/tea/dara"
)

type iListSessionResponseBody interface {
	dara.Model
	String() string
	GoString() string
	SetCode(v string) *ListSessionResponseBody
	GetCode() *string
	SetData(v []*ListSessionResponseBodyData) *ListSessionResponseBody
	GetData() []*ListSessionResponseBodyData
	SetHttpStatusCode(v int32) *ListSessionResponseBody
	GetHttpStatusCode() *int32
	SetMaxResults(v int32) *ListSessionResponseBody
	GetMaxResults() *int32
	SetMessage(v string) *ListSessionResponseBody
	GetMessage() *string
	SetNextToken(v string) *ListSessionResponseBody
	GetNextToken() *string
	SetRequestId(v string) *ListSessionResponseBody
	GetRequestId() *string
	SetSuccess(v bool) *ListSessionResponseBody
	GetSuccess() *bool
	SetTotalCount(v int32) *ListSessionResponseBody
	GetTotalCount() *int32
}

type ListSessionResponseBody struct {
	Code           *string                        `json:"Code,omitempty" xml:"Code,omitempty"`
	Data           []*ListSessionResponseBodyData `json:"Data,omitempty" xml:"Data,omitempty" type:"Repeated"`
	HttpStatusCode *int32                         `json:"HttpStatusCode,omitempty" xml:"HttpStatusCode,omitempty"`
	MaxResults     *int32                         `json:"MaxResults,omitempty" xml:"MaxResults,omitempty"`
	Message        *string                        `json:"Message,omitempty" xml:"Message,omitempty"`
	NextToken      *string                        `json:"NextToken,omitempty" xml:"NextToken,omitempty"`
	RequestId      *string                        `json:"RequestId,omitempty" xml:"RequestId,omitempty"`
	Success        *bool                          `json:"Success,omitempty" xml:"Success,omitempty"`
	TotalCount     *int32                         `json:"TotalCount,omitempty" xml:"TotalCount,omitempty"`
}

func (s ListSessionResponseBody) String() string {
	return dara.Prettify(s)
}

func (s ListSessionResponseBody) GoString() string {
	return s.String()
}

func (s *ListSessionResponseBody) GetCode() *string {
	return s.Code
}

func (s *ListSessionResponseBody) GetData() []*ListSessionResponseBodyData {
	return s.Data
}

func (s *ListSessionResponseBody) GetHttpStatusCode() *int32 {
	return s.HttpStatusCode
}

func (s *ListSessionResponseBody) GetMaxResults() *int32 {
	return s.MaxResults
}

func (s *ListSessionResponseBody) GetMessage() *string {
	return s.Message
}

func (s *ListSessionResponseBody) GetNextToken() *string {
	return s.NextToken
}

func (s *ListSessionResponseBody) GetRequestId() *string {
	return s.RequestId
}

func (s *ListSessionResponseBody) GetSuccess() *bool {
	return s.Success
}

func (s *ListSessionResponseBody) GetTotalCount() *int32 {
	return s.TotalCount
}

func (s *ListSessionResponseBody) SetCode(v string) *ListSessionResponseBody {
	s.Code = &v
	return s
}

func (s *ListSessionResponseBody) SetData(v []*ListSessionResponseBodyData) *ListSessionResponseBody {
	s.Data = v
	return s
}

func (s *ListSessionResponseBody) SetHttpStatusCode(v int32) *ListSessionResponseBody {
	s.HttpStatusCode = &v
	return s
}

func (s *ListSessionResponseBody) SetMaxResults(v int32) *ListSessionResponseBody {
	s.MaxResults = &v
	return s
}

func (s *ListSessionResponseBody) SetMessage(v string) *ListSessionResponseBody {
	s.Message = &v
	return s
}

func (s *ListSessionResponseBody) SetNextToken(v string) *ListSessionResponseBody {
	s.NextToken = &v
	return s
}

func (s *ListSessionResponseBody) SetRequestId(v string) *ListSessionResponseBody {
	s.RequestId = &v
	return s
}

func (s *ListSessionResponseBody) SetSuccess(v bool) *ListSessionResponseBody {
	s.Success = &v
	return s
}

func (s *ListSessionResponseBody) SetTotalCount(v int32) *ListSessionResponseBody {
	s.TotalCount = &v
	return s
}

func (s *ListSessionResponseBody) Validate() error {
	return dara.Validate(s)
}

type ListSessionResponseBodyData struct {
	SessionId     *string `json:"SessionId,omitempty" xml:"SessionId,omitempty"`
	SessionStatus *string `json:"SessionStatus,omitempty" xml:"SessionStatus,omitempty"`
}

func (s ListSessionResponseBodyData) String() string {
	return dara.Prettify(s)
}

func (s ListSessionResponseBodyData) GoString() string {
	return s.String()
}

func (s *ListSessionResponseBodyData) GetSessionId() *string {
	return s.SessionId
}

func (s *ListSessionResponseBodyData) SetSessionId(v string) *ListSessionResponseBodyData {
	s.SessionId = &v
	return s
}

func (s *ListSessionResponseBodyData) GetSessionStatus() *string {
	return s.SessionStatus
}

func (s *ListSessionResponseBodyData) SetSessionStatus(v string) *ListSessionResponseBodyData {
	s.SessionStatus = &v
	return s
}

func (s *ListSessionResponseBodyData) Validate() error {
	return dara.Validate(s)
}
