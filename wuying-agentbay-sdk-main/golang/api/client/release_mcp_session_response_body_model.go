// This file is auto-generated, don't edit it. Thanks.
package client

import (
	"github.com/alibabacloud-go/tea/dara"
)

type iReleaseMcpSessionResponseBody interface {
	dara.Model
	String() string
	GoString() string
	SetCode(v string) *ReleaseMcpSessionResponseBody
	GetCode() *string
	SetHttpStatusCode(v int32) *ReleaseMcpSessionResponseBody
	GetHttpStatusCode() *int32
	SetMessage(v string) *ReleaseMcpSessionResponseBody
	GetMessage() *string
	SetRequestId(v string) *ReleaseMcpSessionResponseBody
	GetRequestId() *string
	SetSuccess(v bool) *ReleaseMcpSessionResponseBody
	GetSuccess() *bool
}

type ReleaseMcpSessionResponseBody struct {
	Code           *string `json:"Code,omitempty" xml:"Code,omitempty"`
	HttpStatusCode *int32  `json:"HttpStatusCode,omitempty" xml:"HttpStatusCode,omitempty"`
	Message        *string `json:"Message,omitempty" xml:"Message,omitempty"`
	RequestId      *string `json:"RequestId,omitempty" xml:"RequestId,omitempty"`
	Success        *bool   `json:"Success,omitempty" xml:"Success,omitempty"`
}

func (s ReleaseMcpSessionResponseBody) String() string {
	return dara.Prettify(s)
}

func (s ReleaseMcpSessionResponseBody) GoString() string {
	return s.String()
}

func (s *ReleaseMcpSessionResponseBody) GetCode() *string {
	return s.Code
}

func (s *ReleaseMcpSessionResponseBody) GetHttpStatusCode() *int32 {
	return s.HttpStatusCode
}

func (s *ReleaseMcpSessionResponseBody) GetMessage() *string {
	return s.Message
}

func (s *ReleaseMcpSessionResponseBody) GetRequestId() *string {
	return s.RequestId
}

func (s *ReleaseMcpSessionResponseBody) GetSuccess() *bool {
	return s.Success
}

func (s *ReleaseMcpSessionResponseBody) SetCode(v string) *ReleaseMcpSessionResponseBody {
	s.Code = &v
	return s
}

func (s *ReleaseMcpSessionResponseBody) SetHttpStatusCode(v int32) *ReleaseMcpSessionResponseBody {
	s.HttpStatusCode = &v
	return s
}

func (s *ReleaseMcpSessionResponseBody) SetMessage(v string) *ReleaseMcpSessionResponseBody {
	s.Message = &v
	return s
}

func (s *ReleaseMcpSessionResponseBody) SetRequestId(v string) *ReleaseMcpSessionResponseBody {
	s.RequestId = &v
	return s
}

func (s *ReleaseMcpSessionResponseBody) SetSuccess(v bool) *ReleaseMcpSessionResponseBody {
	s.Success = &v
	return s
}

func (s *ReleaseMcpSessionResponseBody) Validate() error {
	return dara.Validate(s)
}
