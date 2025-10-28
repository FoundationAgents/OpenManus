package client

import (
	"github.com/alibabacloud-go/tea/dara"
)

type iGetContextFileUploadUrlResponseBody interface {
	dara.Model
	String() string
	GoString() string
	SetCode(v string) *GetContextFileUploadUrlResponseBody
	GetCode() *string
	SetData(v *GetContextFileUploadUrlResponseBodyData) *GetContextFileUploadUrlResponseBody
	GetData() *GetContextFileUploadUrlResponseBodyData
	SetHttpStatusCode(v int32) *GetContextFileUploadUrlResponseBody
	GetHttpStatusCode() *int32
	SetMessage(v string) *GetContextFileUploadUrlResponseBody
	GetMessage() *string
	SetRequestId(v string) *GetContextFileUploadUrlResponseBody
	GetRequestId() *string
	SetSuccess(v bool) *GetContextFileUploadUrlResponseBody
	GetSuccess() *bool
}

type GetContextFileUploadUrlResponseBody struct {
	Code           *string                                  `json:"Code,omitempty" xml:"Code,omitempty"`
	Data           *GetContextFileUploadUrlResponseBodyData `json:"Data,omitempty" xml:"Data,omitempty" type:"Struct"`
	HttpStatusCode *int32                                   `json:"HttpStatusCode,omitempty" xml:"HttpStatusCode,omitempty"`
	Message        *string                                  `json:"Message,omitempty" xml:"Message,omitempty"`
	RequestId      *string                                  `json:"RequestId,omitempty" xml:"RequestId,omitempty"`
	Success        *bool                                    `json:"Success,omitempty" xml:"Success,omitempty"`
}

func (s GetContextFileUploadUrlResponseBody) String() string {
	return dara.Prettify(s)
}

func (s GetContextFileUploadUrlResponseBody) GoString() string {
	return s.String()
}

func (s *GetContextFileUploadUrlResponseBody) GetCode() *string {
	return s.Code
}

func (s *GetContextFileUploadUrlResponseBody) GetData() *GetContextFileUploadUrlResponseBodyData {
	return s.Data
}

func (s *GetContextFileUploadUrlResponseBody) GetHttpStatusCode() *int32 {
	return s.HttpStatusCode
}

func (s *GetContextFileUploadUrlResponseBody) GetMessage() *string {
	return s.Message
}

func (s *GetContextFileUploadUrlResponseBody) GetRequestId() *string {
	return s.RequestId
}

func (s *GetContextFileUploadUrlResponseBody) GetSuccess() *bool {
	return s.Success
}

func (s *GetContextFileUploadUrlResponseBody) SetCode(v string) *GetContextFileUploadUrlResponseBody {
	s.Code = &v
	return s
}

func (s *GetContextFileUploadUrlResponseBody) SetData(v *GetContextFileUploadUrlResponseBodyData) *GetContextFileUploadUrlResponseBody {
	s.Data = v
	return s
}

func (s *GetContextFileUploadUrlResponseBody) SetHttpStatusCode(v int32) *GetContextFileUploadUrlResponseBody {
	s.HttpStatusCode = &v
	return s
}

func (s *GetContextFileUploadUrlResponseBody) SetMessage(v string) *GetContextFileUploadUrlResponseBody {
	s.Message = &v
	return s
}

func (s *GetContextFileUploadUrlResponseBody) SetRequestId(v string) *GetContextFileUploadUrlResponseBody {
	s.RequestId = &v
	return s
}

func (s *GetContextFileUploadUrlResponseBody) SetSuccess(v bool) *GetContextFileUploadUrlResponseBody {
	s.Success = &v
	return s
}

func (s *GetContextFileUploadUrlResponseBody) Validate() error {
	return dara.Validate(s)
}

type GetContextFileUploadUrlResponseBodyData struct {
	ExpireTime *int64  `json:"ExpireTime,omitempty" xml:"ExpireTime,omitempty"`
	Url        *string `json:"Url,omitempty" xml:"Url,omitempty"`
}

func (s GetContextFileUploadUrlResponseBodyData) String() string {
	return dara.Prettify(s)
}

func (s GetContextFileUploadUrlResponseBodyData) GoString() string {
	return s.String()
}

func (s *GetContextFileUploadUrlResponseBodyData) GetExpireTime() *int64 {
	return s.ExpireTime
}

func (s *GetContextFileUploadUrlResponseBodyData) GetUrl() *string {
	return s.Url
}

func (s *GetContextFileUploadUrlResponseBodyData) SetExpireTime(v int64) *GetContextFileUploadUrlResponseBodyData {
	s.ExpireTime = &v
	return s
}

func (s *GetContextFileUploadUrlResponseBodyData) SetUrl(v string) *GetContextFileUploadUrlResponseBodyData {
	s.Url = &v
	return s
}

func (s *GetContextFileUploadUrlResponseBodyData) Validate() error {
	return dara.Validate(s)
}
