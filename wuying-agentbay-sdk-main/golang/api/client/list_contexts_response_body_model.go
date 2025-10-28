// This file is auto-generated, don't edit it. Thanks.
package client

import (
	"github.com/alibabacloud-go/tea/dara"
)

type iListContextsResponseBody interface {
	dara.Model
	String() string
	GoString() string
	SetCode(v string) *ListContextsResponseBody
	GetCode() *string
	SetData(v []*ListContextsResponseBodyData) *ListContextsResponseBody
	GetData() []*ListContextsResponseBodyData
	SetHttpStatusCode(v int32) *ListContextsResponseBody
	GetHttpStatusCode() *int32
	SetMaxResults(v int32) *ListContextsResponseBody
	GetMaxResults() *int32
	SetMessage(v string) *ListContextsResponseBody
	GetMessage() *string
	SetNextToken(v string) *ListContextsResponseBody
	GetNextToken() *string
	SetRequestId(v string) *ListContextsResponseBody
	GetRequestId() *string
	SetSuccess(v bool) *ListContextsResponseBody
	GetSuccess() *bool
	SetTotalCount(v int32) *ListContextsResponseBody
	GetTotalCount() *int32
}

type ListContextsResponseBody struct {
	Code           *string                         `json:"Code,omitempty" xml:"Code,omitempty"`
	Data           []*ListContextsResponseBodyData `json:"Data,omitempty" xml:"Data,omitempty" type:"Repeated"`
	HttpStatusCode *int32                          `json:"HttpStatusCode,omitempty" xml:"HttpStatusCode,omitempty"`
	MaxResults     *int32                          `json:"MaxResults,omitempty" xml:"MaxResults,omitempty"`
	Message        *string                         `json:"Message,omitempty" xml:"Message,omitempty"`
	NextToken      *string                         `json:"NextToken,omitempty" xml:"NextToken,omitempty"`
	RequestId      *string                         `json:"RequestId,omitempty" xml:"RequestId,omitempty"`
	Success        *bool                           `json:"Success,omitempty" xml:"Success,omitempty"`
	TotalCount     *int32                          `json:"TotalCount,omitempty" xml:"TotalCount,omitempty"`
}

func (s ListContextsResponseBody) String() string {
	return dara.Prettify(s)
}

func (s ListContextsResponseBody) GoString() string {
	return s.String()
}

func (s *ListContextsResponseBody) GetCode() *string {
	return s.Code
}

func (s *ListContextsResponseBody) GetData() []*ListContextsResponseBodyData {
	return s.Data
}

func (s *ListContextsResponseBody) GetHttpStatusCode() *int32 {
	return s.HttpStatusCode
}

func (s *ListContextsResponseBody) GetMaxResults() *int32 {
	return s.MaxResults
}

func (s *ListContextsResponseBody) GetMessage() *string {
	return s.Message
}

func (s *ListContextsResponseBody) GetNextToken() *string {
	return s.NextToken
}

func (s *ListContextsResponseBody) GetRequestId() *string {
	return s.RequestId
}

func (s *ListContextsResponseBody) GetSuccess() *bool {
	return s.Success
}

func (s *ListContextsResponseBody) GetTotalCount() *int32 {
	return s.TotalCount
}

func (s *ListContextsResponseBody) SetCode(v string) *ListContextsResponseBody {
	s.Code = &v
	return s
}

func (s *ListContextsResponseBody) SetData(v []*ListContextsResponseBodyData) *ListContextsResponseBody {
	s.Data = v
	return s
}

func (s *ListContextsResponseBody) SetHttpStatusCode(v int32) *ListContextsResponseBody {
	s.HttpStatusCode = &v
	return s
}

func (s *ListContextsResponseBody) SetMaxResults(v int32) *ListContextsResponseBody {
	s.MaxResults = &v
	return s
}

func (s *ListContextsResponseBody) SetMessage(v string) *ListContextsResponseBody {
	s.Message = &v
	return s
}

func (s *ListContextsResponseBody) SetNextToken(v string) *ListContextsResponseBody {
	s.NextToken = &v
	return s
}

func (s *ListContextsResponseBody) SetRequestId(v string) *ListContextsResponseBody {
	s.RequestId = &v
	return s
}

func (s *ListContextsResponseBody) SetSuccess(v bool) *ListContextsResponseBody {
	s.Success = &v
	return s
}

func (s *ListContextsResponseBody) SetTotalCount(v int32) *ListContextsResponseBody {
	s.TotalCount = &v
	return s
}

func (s *ListContextsResponseBody) Validate() error {
	return dara.Validate(s)
}

type ListContextsResponseBodyData struct {
	CreateTime   *string `json:"CreateTime,omitempty" xml:"CreateTime,omitempty"`
	Id           *string `json:"Id,omitempty" xml:"Id,omitempty"`
	LastUsedTime *string `json:"LastUsedTime,omitempty" xml:"LastUsedTime,omitempty"`
	Name         *string `json:"Name,omitempty" xml:"Name,omitempty"`
	OsType       *string `json:"OsType,omitempty" xml:"OsType,omitempty"`
	State        *string `json:"State,omitempty" xml:"State,omitempty"`
}

func (s ListContextsResponseBodyData) String() string {
	return dara.Prettify(s)
}

func (s ListContextsResponseBodyData) GoString() string {
	return s.String()
}

func (s *ListContextsResponseBodyData) GetCreateTime() *string {
	return s.CreateTime
}

func (s *ListContextsResponseBodyData) GetId() *string {
	return s.Id
}

func (s *ListContextsResponseBodyData) GetLastUsedTime() *string {
	return s.LastUsedTime
}

func (s *ListContextsResponseBodyData) GetName() *string {
	return s.Name
}

func (s *ListContextsResponseBodyData) GetOsType() *string {
	return s.OsType
}

func (s *ListContextsResponseBodyData) GetState() *string {
	return s.State
}

func (s *ListContextsResponseBodyData) SetCreateTime(v string) *ListContextsResponseBodyData {
	s.CreateTime = &v
	return s
}

func (s *ListContextsResponseBodyData) SetId(v string) *ListContextsResponseBodyData {
	s.Id = &v
	return s
}

func (s *ListContextsResponseBodyData) SetLastUsedTime(v string) *ListContextsResponseBodyData {
	s.LastUsedTime = &v
	return s
}

func (s *ListContextsResponseBodyData) SetName(v string) *ListContextsResponseBodyData {
	s.Name = &v
	return s
}

func (s *ListContextsResponseBodyData) SetOsType(v string) *ListContextsResponseBodyData {
	s.OsType = &v
	return s
}

func (s *ListContextsResponseBodyData) SetState(v string) *ListContextsResponseBodyData {
	s.State = &v
	return s
}

func (s *ListContextsResponseBodyData) Validate() error {
	return dara.Validate(s)
}
