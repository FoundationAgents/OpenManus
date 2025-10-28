// This file is auto-generated, don't edit it. Thanks.
package client

import (
	"github.com/alibabacloud-go/tea/dara"
)

type iModifyContextResponseBody interface {
	dara.Model
	String() string
	GoString() string
	SetCode(v string) *ModifyContextResponseBody
	GetCode() *string
	SetHttpStatusCode(v int32) *ModifyContextResponseBody
	GetHttpStatusCode() *int32
	SetMessage(v string) *ModifyContextResponseBody
	GetMessage() *string
	SetRequestId(v string) *ModifyContextResponseBody
	GetRequestId() *string
	SetSuccess(v bool) *ModifyContextResponseBody
	GetSuccess() *bool
}

type ModifyContextResponseBody struct {
	Code           *string `json:"Code,omitempty" xml:"Code,omitempty"`
	HttpStatusCode *int32  `json:"HttpStatusCode,omitempty" xml:"HttpStatusCode,omitempty"`
	Message        *string `json:"Message,omitempty" xml:"Message,omitempty"`
	RequestId      *string `json:"RequestId,omitempty" xml:"RequestId,omitempty"`
	Success        *bool   `json:"Success,omitempty" xml:"Success,omitempty"`
}

func (s ModifyContextResponseBody) String() string {
	return dara.Prettify(s)
}

func (s ModifyContextResponseBody) GoString() string {
	return s.String()
}

func (s *ModifyContextResponseBody) GetCode() *string {
	return s.Code
}

func (s *ModifyContextResponseBody) GetHttpStatusCode() *int32 {
	return s.HttpStatusCode
}

func (s *ModifyContextResponseBody) GetMessage() *string {
	return s.Message
}

func (s *ModifyContextResponseBody) GetRequestId() *string {
	return s.RequestId
}

func (s *ModifyContextResponseBody) GetSuccess() *bool {
	return s.Success
}

func (s *ModifyContextResponseBody) SetCode(v string) *ModifyContextResponseBody {
	s.Code = &v
	return s
}

func (s *ModifyContextResponseBody) SetHttpStatusCode(v int32) *ModifyContextResponseBody {
	s.HttpStatusCode = &v
	return s
}

func (s *ModifyContextResponseBody) SetMessage(v string) *ModifyContextResponseBody {
	s.Message = &v
	return s
}

func (s *ModifyContextResponseBody) SetRequestId(v string) *ModifyContextResponseBody {
	s.RequestId = &v
	return s
}

func (s *ModifyContextResponseBody) SetSuccess(v bool) *ModifyContextResponseBody {
	s.Success = &v
	return s
}

func (s *ModifyContextResponseBody) Validate() error {
	return dara.Validate(s)
}
