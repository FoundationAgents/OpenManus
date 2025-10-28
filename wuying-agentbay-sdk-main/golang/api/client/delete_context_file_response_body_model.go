package client

import (
	"github.com/alibabacloud-go/tea/dara"
)

type iDeleteContextFileResponseBody interface {
	dara.Model
	String() string
	GoString() string
	SetCode(v string) *DeleteContextFileResponseBody
	GetCode() *string
	SetHttpStatusCode(v int32) *DeleteContextFileResponseBody
	GetHttpStatusCode() *int32
	SetMessage(v string) *DeleteContextFileResponseBody
	GetMessage() *string
	SetRequestId(v string) *DeleteContextFileResponseBody
	GetRequestId() *string
	SetSuccess(v bool) *DeleteContextFileResponseBody
	GetSuccess() *bool
}

type DeleteContextFileResponseBody struct {
	Code           *string `json:"Code,omitempty" xml:"Code,omitempty"`
	HttpStatusCode *int32  `json:"HttpStatusCode,omitempty" xml:"HttpStatusCode,omitempty"`
	Message        *string `json:"Message,omitempty" xml:"Message,omitempty"`
	RequestId      *string `json:"RequestId,omitempty" xml:"RequestId,omitempty"`
	Success        *bool   `json:"Success,omitempty" xml:"Success,omitempty"`
}

func (s DeleteContextFileResponseBody) String() string {
	return dara.Prettify(s)
}

func (s DeleteContextFileResponseBody) GoString() string {
	return s.String()
}

func (s *DeleteContextFileResponseBody) GetCode() *string {
	return s.Code
}

func (s *DeleteContextFileResponseBody) GetHttpStatusCode() *int32 {
	return s.HttpStatusCode
}

func (s *DeleteContextFileResponseBody) GetMessage() *string {
	return s.Message
}

func (s *DeleteContextFileResponseBody) GetRequestId() *string {
	return s.RequestId
}

func (s *DeleteContextFileResponseBody) GetSuccess() *bool {
	return s.Success
}

func (s *DeleteContextFileResponseBody) SetCode(v string) *DeleteContextFileResponseBody {
	s.Code = &v
	return s
}

func (s *DeleteContextFileResponseBody) SetHttpStatusCode(v int32) *DeleteContextFileResponseBody {
	s.HttpStatusCode = &v
	return s
}

func (s *DeleteContextFileResponseBody) SetMessage(v string) *DeleteContextFileResponseBody {
	s.Message = &v
	return s
}

func (s *DeleteContextFileResponseBody) SetRequestId(v string) *DeleteContextFileResponseBody {
	s.RequestId = &v
	return s
}

func (s *DeleteContextFileResponseBody) SetSuccess(v bool) *DeleteContextFileResponseBody {
	s.Success = &v
	return s
}

func (s *DeleteContextFileResponseBody) Validate() error {
	return dara.Validate(s)
}
