// This file is auto-generated, don't edit it. Thanks.
package client

import (
	"github.com/alibabacloud-go/tea/dara"
)

type iGetContextInfoResponseBody interface {
	dara.Model
	String() string
	GoString() string
	SetCode(v string) *GetContextInfoResponseBody
	GetCode() *string
	SetData(v *GetContextInfoResponseBodyData) *GetContextInfoResponseBody
	GetData() *GetContextInfoResponseBodyData
	SetHttpStatusCode(v int32) *GetContextInfoResponseBody
	GetHttpStatusCode() *int32
	SetMessage(v string) *GetContextInfoResponseBody
	GetMessage() *string
	SetRequestId(v string) *GetContextInfoResponseBody
	GetRequestId() *string
	SetSuccess(v bool) *GetContextInfoResponseBody
	GetSuccess() *bool
}

type GetContextInfoResponseBody struct {
	Code           *string                         `json:"Code,omitempty" xml:"Code,omitempty"`
	Data           *GetContextInfoResponseBodyData `json:"Data,omitempty" xml:"Data,omitempty" type:"Struct"`
	HttpStatusCode *int32                          `json:"HttpStatusCode,omitempty" xml:"HttpStatusCode,omitempty"`
	Message        *string                         `json:"Message,omitempty" xml:"Message,omitempty"`
	RequestId      *string                         `json:"RequestId,omitempty" xml:"RequestId,omitempty"`
	Success        *bool                           `json:"Success,omitempty" xml:"Success,omitempty"`
}

func (s GetContextInfoResponseBody) String() string {
	return dara.Prettify(s)
}

func (s GetContextInfoResponseBody) GoString() string {
	return s.String()
}

func (s *GetContextInfoResponseBody) GetCode() *string {
	return s.Code
}

func (s *GetContextInfoResponseBody) GetData() *GetContextInfoResponseBodyData {
	return s.Data
}

func (s *GetContextInfoResponseBody) GetHttpStatusCode() *int32 {
	return s.HttpStatusCode
}

func (s *GetContextInfoResponseBody) GetMessage() *string {
	return s.Message
}

func (s *GetContextInfoResponseBody) GetRequestId() *string {
	return s.RequestId
}

func (s *GetContextInfoResponseBody) GetSuccess() *bool {
	return s.Success
}

func (s *GetContextInfoResponseBody) SetCode(v string) *GetContextInfoResponseBody {
	s.Code = &v
	return s
}

func (s *GetContextInfoResponseBody) SetData(v *GetContextInfoResponseBodyData) *GetContextInfoResponseBody {
	s.Data = v
	return s
}

func (s *GetContextInfoResponseBody) SetHttpStatusCode(v int32) *GetContextInfoResponseBody {
	s.HttpStatusCode = &v
	return s
}

func (s *GetContextInfoResponseBody) SetMessage(v string) *GetContextInfoResponseBody {
	s.Message = &v
	return s
}

func (s *GetContextInfoResponseBody) SetRequestId(v string) *GetContextInfoResponseBody {
	s.RequestId = &v
	return s
}

func (s *GetContextInfoResponseBody) SetSuccess(v bool) *GetContextInfoResponseBody {
	s.Success = &v
	return s
}

func (s *GetContextInfoResponseBody) Validate() error {
	return dara.Validate(s)
}

type GetContextInfoResponseBodyData struct {
	ContextStatus *string `json:"ContextStatus,omitempty" xml:"ContextStatus,omitempty"`
}

func (s GetContextInfoResponseBodyData) String() string {
	return dara.Prettify(s)
}

func (s GetContextInfoResponseBodyData) GoString() string {
	return s.String()
}

func (s *GetContextInfoResponseBodyData) GetContextStatus() *string {
	return s.ContextStatus
}

func (s *GetContextInfoResponseBodyData) SetContextStatus(v string) *GetContextInfoResponseBodyData {
	s.ContextStatus = &v
	return s
}

func (s *GetContextInfoResponseBodyData) Validate() error {
	return dara.Validate(s)
}
