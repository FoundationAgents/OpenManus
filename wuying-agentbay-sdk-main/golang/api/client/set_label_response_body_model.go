// This file is auto-generated, don't edit it. Thanks.
package client

import (
	"github.com/alibabacloud-go/tea/dara"
)

type iSetLabelResponseBody interface {
	dara.Model
	String() string
	GoString() string
	SetCode(v string) *SetLabelResponseBody
	GetCode() *string
	SetHttpStatusCode(v int32) *SetLabelResponseBody
	GetHttpStatusCode() *int32
	SetMessage(v string) *SetLabelResponseBody
	GetMessage() *string
	SetRequestId(v string) *SetLabelResponseBody
	GetRequestId() *string
	SetSuccess(v bool) *SetLabelResponseBody
	GetSuccess() *bool
}

type SetLabelResponseBody struct {
	Code           *string `json:"Code,omitempty" xml:"Code,omitempty"`
	HttpStatusCode *int32  `json:"HttpStatusCode,omitempty" xml:"HttpStatusCode,omitempty"`
	Message        *string `json:"Message,omitempty" xml:"Message,omitempty"`
	RequestId      *string `json:"RequestId,omitempty" xml:"RequestId,omitempty"`
	Success        *bool   `json:"Success,omitempty" xml:"Success,omitempty"`
}

func (s SetLabelResponseBody) String() string {
	return dara.Prettify(s)
}

func (s SetLabelResponseBody) GoString() string {
	return s.String()
}

func (s *SetLabelResponseBody) GetCode() *string {
	return s.Code
}

func (s *SetLabelResponseBody) GetHttpStatusCode() *int32 {
	return s.HttpStatusCode
}

func (s *SetLabelResponseBody) GetMessage() *string {
	return s.Message
}

func (s *SetLabelResponseBody) GetRequestId() *string {
	return s.RequestId
}

func (s *SetLabelResponseBody) GetSuccess() *bool {
	return s.Success
}

func (s *SetLabelResponseBody) SetCode(v string) *SetLabelResponseBody {
	s.Code = &v
	return s
}

func (s *SetLabelResponseBody) SetHttpStatusCode(v int32) *SetLabelResponseBody {
	s.HttpStatusCode = &v
	return s
}

func (s *SetLabelResponseBody) SetMessage(v string) *SetLabelResponseBody {
	s.Message = &v
	return s
}

func (s *SetLabelResponseBody) SetRequestId(v string) *SetLabelResponseBody {
	s.RequestId = &v
	return s
}

func (s *SetLabelResponseBody) SetSuccess(v bool) *SetLabelResponseBody {
	s.Success = &v
	return s
}

func (s *SetLabelResponseBody) Validate() error {
	return dara.Validate(s)
}
