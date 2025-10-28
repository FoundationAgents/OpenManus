package client

import (
	"github.com/alibabacloud-go/tea/dara"
)

type iGetContextFileDownloadUrlResponseBody interface {
	dara.Model
	String() string
	GoString() string
	SetCode(v string) *GetContextFileDownloadUrlResponseBody
	GetCode() *string
	SetData(v *GetContextFileDownloadUrlResponseBodyData) *GetContextFileDownloadUrlResponseBody
	GetData() *GetContextFileDownloadUrlResponseBodyData
	SetHttpStatusCode(v int32) *GetContextFileDownloadUrlResponseBody
	GetHttpStatusCode() *int32
	SetMessage(v string) *GetContextFileDownloadUrlResponseBody
	GetMessage() *string
	SetRequestId(v string) *GetContextFileDownloadUrlResponseBody
	GetRequestId() *string
	SetSuccess(v bool) *GetContextFileDownloadUrlResponseBody
	GetSuccess() *bool
}

type GetContextFileDownloadUrlResponseBody struct {
	Code           *string                                    `json:"Code,omitempty" xml:"Code,omitempty"`
	Data           *GetContextFileDownloadUrlResponseBodyData `json:"Data,omitempty" xml:"Data,omitempty" type:"Struct"`
	HttpStatusCode *int32                                     `json:"HttpStatusCode,omitempty" xml:"HttpStatusCode,omitempty"`
	Message        *string                                    `json:"Message,omitempty" xml:"Message,omitempty"`
	RequestId      *string                                    `json:"RequestId,omitempty" xml:"RequestId,omitempty"`
	Success        *bool                                      `json:"Success,omitempty" xml:"Success,omitempty"`
}

func (s GetContextFileDownloadUrlResponseBody) String() string {
	return dara.Prettify(s)
}

func (s GetContextFileDownloadUrlResponseBody) GoString() string {
	return s.String()
}

func (s *GetContextFileDownloadUrlResponseBody) GetCode() *string {
	return s.Code
}

func (s *GetContextFileDownloadUrlResponseBody) GetData() *GetContextFileDownloadUrlResponseBodyData {
	return s.Data
}

func (s *GetContextFileDownloadUrlResponseBody) GetHttpStatusCode() *int32 {
	return s.HttpStatusCode
}

func (s *GetContextFileDownloadUrlResponseBody) GetMessage() *string {
	return s.Message
}

func (s *GetContextFileDownloadUrlResponseBody) GetRequestId() *string {
	return s.RequestId
}

func (s *GetContextFileDownloadUrlResponseBody) GetSuccess() *bool {
	return s.Success
}

func (s *GetContextFileDownloadUrlResponseBody) SetCode(v string) *GetContextFileDownloadUrlResponseBody {
	s.Code = &v
	return s
}

func (s *GetContextFileDownloadUrlResponseBody) SetData(v *GetContextFileDownloadUrlResponseBodyData) *GetContextFileDownloadUrlResponseBody {
	s.Data = v
	return s
}

func (s *GetContextFileDownloadUrlResponseBody) SetHttpStatusCode(v int32) *GetContextFileDownloadUrlResponseBody {
	s.HttpStatusCode = &v
	return s
}

func (s *GetContextFileDownloadUrlResponseBody) SetMessage(v string) *GetContextFileDownloadUrlResponseBody {
	s.Message = &v
	return s
}

func (s *GetContextFileDownloadUrlResponseBody) SetRequestId(v string) *GetContextFileDownloadUrlResponseBody {
	s.RequestId = &v
	return s
}

func (s *GetContextFileDownloadUrlResponseBody) SetSuccess(v bool) *GetContextFileDownloadUrlResponseBody {
	s.Success = &v
	return s
}

func (s *GetContextFileDownloadUrlResponseBody) Validate() error {
	return dara.Validate(s)
}

type GetContextFileDownloadUrlResponseBodyData struct {
	ExpireTime *int64  `json:"ExpireTime,omitempty" xml:"ExpireTime,omitempty"`
	Url        *string `json:"Url,omitempty" xml:"Url,omitempty"`
}

func (s GetContextFileDownloadUrlResponseBodyData) String() string {
	return dara.Prettify(s)
}

func (s GetContextFileDownloadUrlResponseBodyData) GoString() string {
	return s.String()
}

func (s *GetContextFileDownloadUrlResponseBodyData) GetExpireTime() *int64 {
	return s.ExpireTime
}

func (s *GetContextFileDownloadUrlResponseBodyData) GetUrl() *string {
	return s.Url
}

func (s *GetContextFileDownloadUrlResponseBodyData) SetExpireTime(v int64) *GetContextFileDownloadUrlResponseBodyData {
	s.ExpireTime = &v
	return s
}

func (s *GetContextFileDownloadUrlResponseBodyData) SetUrl(v string) *GetContextFileDownloadUrlResponseBodyData {
	s.Url = &v
	return s
}

func (s *GetContextFileDownloadUrlResponseBodyData) Validate() error {
	return dara.Validate(s)
}
