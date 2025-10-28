// This file is auto-generated, don't edit it. Thanks.
package client

import (
	"github.com/alibabacloud-go/tea/dara"
)

type iCallMcpToolResponseBody interface {
	dara.Model
	String() string
	GoString() string
	SetCode(v string) *CallMcpToolResponseBody
	GetCode() *string
	SetData(v interface{}) *CallMcpToolResponseBody
	GetData() interface{}
	SetHttpStatusCode(v int32) *CallMcpToolResponseBody
	GetHttpStatusCode() *int32
	SetMessage(v string) *CallMcpToolResponseBody
	GetMessage() *string
	SetRequestId(v string) *CallMcpToolResponseBody
	GetRequestId() *string
	SetSuccess(v bool) *CallMcpToolResponseBody
	GetSuccess() *bool
}

type CallMcpToolResponseBody struct {
	Code           *string     `json:"Code,omitempty" xml:"Code,omitempty"`
	Data           interface{} `json:"Data,omitempty" xml:"Data,omitempty"`
	HttpStatusCode *int32      `json:"HttpStatusCode,omitempty" xml:"HttpStatusCode,omitempty"`
	Message        *string     `json:"Message,omitempty" xml:"Message,omitempty"`
	RequestId      *string     `json:"RequestId,omitempty" xml:"RequestId,omitempty"`
	Success        *bool       `json:"Success,omitempty" xml:"Success,omitempty"`
}

func (s CallMcpToolResponseBody) String() string {
	return dara.Prettify(s)
}

func (s CallMcpToolResponseBody) GoString() string {
	return s.String()
}

func (s *CallMcpToolResponseBody) GetCode() *string {
	return s.Code
}

func (s *CallMcpToolResponseBody) GetData() interface{} {
	return s.Data
}

func (s *CallMcpToolResponseBody) GetHttpStatusCode() *int32 {
	return s.HttpStatusCode
}

func (s *CallMcpToolResponseBody) GetMessage() *string {
	return s.Message
}

func (s *CallMcpToolResponseBody) GetRequestId() *string {
	return s.RequestId
}

func (s *CallMcpToolResponseBody) GetSuccess() *bool {
	return s.Success
}

func (s *CallMcpToolResponseBody) SetCode(v string) *CallMcpToolResponseBody {
	s.Code = &v
	return s
}

func (s *CallMcpToolResponseBody) SetData(v interface{}) *CallMcpToolResponseBody {
	s.Data = v
	return s
}

func (s *CallMcpToolResponseBody) SetHttpStatusCode(v int32) *CallMcpToolResponseBody {
	s.HttpStatusCode = &v
	return s
}

func (s *CallMcpToolResponseBody) SetMessage(v string) *CallMcpToolResponseBody {
	s.Message = &v
	return s
}

func (s *CallMcpToolResponseBody) SetRequestId(v string) *CallMcpToolResponseBody {
	s.RequestId = &v
	return s
}

func (s *CallMcpToolResponseBody) SetSuccess(v bool) *CallMcpToolResponseBody {
	s.Success = &v
	return s
}

func (s *CallMcpToolResponseBody) Validate() error {
	return dara.Validate(s)
}
