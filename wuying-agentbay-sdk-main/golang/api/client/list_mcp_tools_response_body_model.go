// This file is auto-generated, don't edit it. Thanks.
package client

import (
	"github.com/alibabacloud-go/tea/dara"
)

type iListMcpToolsResponseBody interface {
	dara.Model
	String() string
	GoString() string
	SetCode(v string) *ListMcpToolsResponseBody
	GetCode() *string
	SetData(v string) *ListMcpToolsResponseBody
	GetData() *string
	SetHttpStatusCode(v int32) *ListMcpToolsResponseBody
	GetHttpStatusCode() *int32
	SetMessage(v string) *ListMcpToolsResponseBody
	GetMessage() *string
	SetRequestId(v string) *ListMcpToolsResponseBody
	GetRequestId() *string
	SetSuccess(v bool) *ListMcpToolsResponseBody
	GetSuccess() *bool
}

type ListMcpToolsResponseBody struct {
	Code           *string `json:"Code,omitempty" xml:"Code,omitempty"`
	Data           *string `json:"Data,omitempty" xml:"Data,omitempty"`
	HttpStatusCode *int32  `json:"HttpStatusCode,omitempty" xml:"HttpStatusCode,omitempty"`
	Message        *string `json:"Message,omitempty" xml:"Message,omitempty"`
	RequestId      *string `json:"RequestId,omitempty" xml:"RequestId,omitempty"`
	Success        *bool   `json:"Success,omitempty" xml:"Success,omitempty"`
}

func (s ListMcpToolsResponseBody) String() string {
	return dara.Prettify(s)
}

func (s ListMcpToolsResponseBody) GoString() string {
	return s.String()
}

func (s *ListMcpToolsResponseBody) GetCode() *string {
	return s.Code
}

func (s *ListMcpToolsResponseBody) GetData() *string {
	return s.Data
}

func (s *ListMcpToolsResponseBody) GetHttpStatusCode() *int32 {
	return s.HttpStatusCode
}

func (s *ListMcpToolsResponseBody) GetMessage() *string {
	return s.Message
}

func (s *ListMcpToolsResponseBody) GetRequestId() *string {
	return s.RequestId
}

func (s *ListMcpToolsResponseBody) GetSuccess() *bool {
	return s.Success
}

func (s *ListMcpToolsResponseBody) SetCode(v string) *ListMcpToolsResponseBody {
	s.Code = &v
	return s
}

func (s *ListMcpToolsResponseBody) SetData(v string) *ListMcpToolsResponseBody {
	s.Data = &v
	return s
}

func (s *ListMcpToolsResponseBody) SetHttpStatusCode(v int32) *ListMcpToolsResponseBody {
	s.HttpStatusCode = &v
	return s
}

func (s *ListMcpToolsResponseBody) SetMessage(v string) *ListMcpToolsResponseBody {
	s.Message = &v
	return s
}

func (s *ListMcpToolsResponseBody) SetRequestId(v string) *ListMcpToolsResponseBody {
	s.RequestId = &v
	return s
}

func (s *ListMcpToolsResponseBody) SetSuccess(v bool) *ListMcpToolsResponseBody {
	s.Success = &v
	return s
}

func (s *ListMcpToolsResponseBody) Validate() error {
	return dara.Validate(s)
}
