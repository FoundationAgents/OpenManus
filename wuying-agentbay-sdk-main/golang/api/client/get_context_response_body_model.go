// This file is auto-generated, don't edit it. Thanks.
package client

import (
	"github.com/alibabacloud-go/tea/dara"
)

type iGetContextResponseBody interface {
	dara.Model
	String() string
	GoString() string
	SetCode(v string) *GetContextResponseBody
	GetCode() *string
	SetData(v *GetContextResponseBodyData) *GetContextResponseBody
	GetData() *GetContextResponseBodyData
	SetHttpStatusCode(v int32) *GetContextResponseBody
	GetHttpStatusCode() *int32
	SetMessage(v string) *GetContextResponseBody
	GetMessage() *string
	SetRequestId(v string) *GetContextResponseBody
	GetRequestId() *string
	SetSuccess(v bool) *GetContextResponseBody
	GetSuccess() *bool
}

type GetContextResponseBody struct {
	Code           *string                     `json:"Code,omitempty" xml:"Code,omitempty"`
	Data           *GetContextResponseBodyData `json:"Data,omitempty" xml:"Data,omitempty" type:"Struct"`
	HttpStatusCode *int32                      `json:"HttpStatusCode,omitempty" xml:"HttpStatusCode,omitempty"`
	Message        *string                     `json:"Message,omitempty" xml:"Message,omitempty"`
	RequestId      *string                     `json:"RequestId,omitempty" xml:"RequestId,omitempty"`
	Success        *bool                       `json:"Success,omitempty" xml:"Success,omitempty"`
}

func (s GetContextResponseBody) String() string {
	return dara.Prettify(s)
}

func (s GetContextResponseBody) GoString() string {
	return s.String()
}

func (s *GetContextResponseBody) GetCode() *string {
	return s.Code
}

func (s *GetContextResponseBody) GetData() *GetContextResponseBodyData {
	return s.Data
}

func (s *GetContextResponseBody) GetHttpStatusCode() *int32 {
	return s.HttpStatusCode
}

func (s *GetContextResponseBody) GetMessage() *string {
	return s.Message
}

func (s *GetContextResponseBody) GetRequestId() *string {
	return s.RequestId
}

func (s *GetContextResponseBody) GetSuccess() *bool {
	return s.Success
}

func (s *GetContextResponseBody) SetCode(v string) *GetContextResponseBody {
	s.Code = &v
	return s
}

func (s *GetContextResponseBody) SetData(v *GetContextResponseBodyData) *GetContextResponseBody {
	s.Data = v
	return s
}

func (s *GetContextResponseBody) SetHttpStatusCode(v int32) *GetContextResponseBody {
	s.HttpStatusCode = &v
	return s
}

func (s *GetContextResponseBody) SetMessage(v string) *GetContextResponseBody {
	s.Message = &v
	return s
}

func (s *GetContextResponseBody) SetRequestId(v string) *GetContextResponseBody {
	s.RequestId = &v
	return s
}

func (s *GetContextResponseBody) SetSuccess(v bool) *GetContextResponseBody {
	s.Success = &v
	return s
}

func (s *GetContextResponseBody) Validate() error {
	return dara.Validate(s)
}

type GetContextResponseBodyData struct {
	CreateTime   *string `json:"CreateTime,omitempty" xml:"CreateTime,omitempty"`
	Id           *string `json:"Id,omitempty" xml:"Id,omitempty"`
	LastUsedTime *string `json:"LastUsedTime,omitempty" xml:"LastUsedTime,omitempty"`
	Name         *string `json:"Name,omitempty" xml:"Name,omitempty"`
	OsType       *string `json:"OsType,omitempty" xml:"OsType,omitempty"`
	State        *string `json:"State,omitempty" xml:"State,omitempty"`
}

func (s GetContextResponseBodyData) String() string {
	return dara.Prettify(s)
}

func (s GetContextResponseBodyData) GoString() string {
	return s.String()
}

func (s *GetContextResponseBodyData) GetCreateTime() *string {
	return s.CreateTime
}

func (s *GetContextResponseBodyData) GetId() *string {
	return s.Id
}

func (s *GetContextResponseBodyData) GetLastUsedTime() *string {
	return s.LastUsedTime
}

func (s *GetContextResponseBodyData) GetName() *string {
	return s.Name
}

func (s *GetContextResponseBodyData) GetOsType() *string {
	return s.OsType
}

func (s *GetContextResponseBodyData) GetState() *string {
	return s.State
}

func (s *GetContextResponseBodyData) SetCreateTime(v string) *GetContextResponseBodyData {
	s.CreateTime = &v
	return s
}

func (s *GetContextResponseBodyData) SetId(v string) *GetContextResponseBodyData {
	s.Id = &v
	return s
}

func (s *GetContextResponseBodyData) SetLastUsedTime(v string) *GetContextResponseBodyData {
	s.LastUsedTime = &v
	return s
}

func (s *GetContextResponseBodyData) SetName(v string) *GetContextResponseBodyData {
	s.Name = &v
	return s
}

func (s *GetContextResponseBodyData) SetOsType(v string) *GetContextResponseBodyData {
	s.OsType = &v
	return s
}

func (s *GetContextResponseBodyData) SetState(v string) *GetContextResponseBodyData {
	s.State = &v
	return s
}

func (s *GetContextResponseBodyData) Validate() error {
	return dara.Validate(s)
}
