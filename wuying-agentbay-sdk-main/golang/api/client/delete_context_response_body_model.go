// This file is auto-generated, don't edit it. Thanks.
package client

import (
	"github.com/alibabacloud-go/tea/dara"
)

type iDeleteContextResponseBody interface {
	dara.Model
	String() string
	GoString() string
	SetCode(v string) *DeleteContextResponseBody
	GetCode() *string
	SetHttpStatusCode(v int32) *DeleteContextResponseBody
	GetHttpStatusCode() *int32
	SetMessage(v string) *DeleteContextResponseBody
	GetMessage() *string
	SetRequestId(v string) *DeleteContextResponseBody
	GetRequestId() *string
	SetSuccess(v bool) *DeleteContextResponseBody
	GetSuccess() *bool
}

type DeleteContextResponseBody struct {
	Code           *string `json:"Code,omitempty" xml:"Code,omitempty"`
	HttpStatusCode *int32  `json:"HttpStatusCode,omitempty" xml:"HttpStatusCode,omitempty"`
	Message        *string `json:"Message,omitempty" xml:"Message,omitempty"`
	RequestId      *string `json:"RequestId,omitempty" xml:"RequestId,omitempty"`
	Success        *bool   `json:"Success,omitempty" xml:"Success,omitempty"`
}

func (s DeleteContextResponseBody) String() string {
	return dara.Prettify(s)
}

func (s DeleteContextResponseBody) GoString() string {
	return s.String()
}

func (s *DeleteContextResponseBody) GetCode() *string {
	return s.Code
}

func (s *DeleteContextResponseBody) GetHttpStatusCode() *int32 {
	return s.HttpStatusCode
}

func (s *DeleteContextResponseBody) GetMessage() *string {
	return s.Message
}

func (s *DeleteContextResponseBody) GetRequestId() *string {
	return s.RequestId
}

func (s *DeleteContextResponseBody) GetSuccess() *bool {
	return s.Success
}

func (s *DeleteContextResponseBody) SetCode(v string) *DeleteContextResponseBody {
	s.Code = &v
	return s
}

func (s *DeleteContextResponseBody) SetHttpStatusCode(v int32) *DeleteContextResponseBody {
	s.HttpStatusCode = &v
	return s
}

func (s *DeleteContextResponseBody) SetMessage(v string) *DeleteContextResponseBody {
	s.Message = &v
	return s
}

func (s *DeleteContextResponseBody) SetRequestId(v string) *DeleteContextResponseBody {
	s.RequestId = &v
	return s
}

func (s *DeleteContextResponseBody) SetSuccess(v bool) *DeleteContextResponseBody {
	s.Success = &v
	return s
}

func (s *DeleteContextResponseBody) Validate() error {
	return dara.Validate(s)
}
