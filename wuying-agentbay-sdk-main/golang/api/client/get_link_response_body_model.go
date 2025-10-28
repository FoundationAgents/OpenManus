// This file is auto-generated, don't edit it. Thanks.
package client

import (
	"github.com/alibabacloud-go/tea/dara"
)

type iGetLinkResponseBody interface {
	dara.Model
	String() string
	GoString() string
	SetCode(v string) *GetLinkResponseBody
	GetCode() *string
	SetData(v *GetLinkResponseBodyData) *GetLinkResponseBody
	GetData() *GetLinkResponseBodyData
	SetHttpStatusCode(v int32) *GetLinkResponseBody
	GetHttpStatusCode() *int32
	SetMessage(v string) *GetLinkResponseBody
	GetMessage() *string
	SetRequestId(v string) *GetLinkResponseBody
	GetRequestId() *string
	SetSuccess(v bool) *GetLinkResponseBody
	GetSuccess() *bool
}

type GetLinkResponseBody struct {
	Code           *string                  `json:"Code,omitempty" xml:"Code,omitempty"`
	Data           *GetLinkResponseBodyData `json:"Data,omitempty" xml:"Data,omitempty" type:"Struct"`
	HttpStatusCode *int32                   `json:"HttpStatusCode,omitempty" xml:"HttpStatusCode,omitempty"`
	Message        *string                  `json:"Message,omitempty" xml:"Message,omitempty"`
	RequestId      *string                  `json:"RequestId,omitempty" xml:"RequestId,omitempty"`
	Success        *bool                    `json:"Success,omitempty" xml:"Success,omitempty"`
}

func (s GetLinkResponseBody) String() string {
	return dara.Prettify(s)
}

func (s GetLinkResponseBody) GoString() string {
	return s.String()
}

func (s *GetLinkResponseBody) GetCode() *string {
	return s.Code
}

func (s *GetLinkResponseBody) GetData() *GetLinkResponseBodyData {
	return s.Data
}

func (s *GetLinkResponseBody) GetHttpStatusCode() *int32 {
	return s.HttpStatusCode
}

func (s *GetLinkResponseBody) GetMessage() *string {
	return s.Message
}

func (s *GetLinkResponseBody) GetRequestId() *string {
	return s.RequestId
}

func (s *GetLinkResponseBody) GetSuccess() *bool {
	return s.Success
}

func (s *GetLinkResponseBody) SetCode(v string) *GetLinkResponseBody {
	s.Code = &v
	return s
}

func (s *GetLinkResponseBody) SetData(v *GetLinkResponseBodyData) *GetLinkResponseBody {
	s.Data = v
	return s
}

func (s *GetLinkResponseBody) SetHttpStatusCode(v int32) *GetLinkResponseBody {
	s.HttpStatusCode = &v
	return s
}

func (s *GetLinkResponseBody) SetMessage(v string) *GetLinkResponseBody {
	s.Message = &v
	return s
}

func (s *GetLinkResponseBody) SetRequestId(v string) *GetLinkResponseBody {
	s.RequestId = &v
	return s
}

func (s *GetLinkResponseBody) SetSuccess(v bool) *GetLinkResponseBody {
	s.Success = &v
	return s
}

func (s *GetLinkResponseBody) Validate() error {
	return dara.Validate(s)
}

type GetLinkResponseBodyData struct {
	Url *string `json:"Url,omitempty" xml:"Url,omitempty"`
}

func (s GetLinkResponseBodyData) String() string {
	return dara.Prettify(s)
}

func (s GetLinkResponseBodyData) GoString() string {
	return s.String()
}

func (s *GetLinkResponseBodyData) GetUrl() *string {
	return s.Url
}

func (s *GetLinkResponseBodyData) SetUrl(v string) *GetLinkResponseBodyData {
	s.Url = &v
	return s
}

func (s *GetLinkResponseBodyData) Validate() error {
	return dara.Validate(s)
}
