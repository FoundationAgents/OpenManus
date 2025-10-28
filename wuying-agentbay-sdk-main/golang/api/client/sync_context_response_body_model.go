// This file is auto-generated, don't edit it. Thanks.
package client

import (
	"github.com/alibabacloud-go/tea/dara"
)

type iSyncContextResponseBody interface {
	dara.Model
	String() string
	GoString() string
	SetCode(v string) *SyncContextResponseBody
	GetCode() *string
	SetHttpStatusCode(v int32) *SyncContextResponseBody
	GetHttpStatusCode() *int32
	SetMessage(v string) *SyncContextResponseBody
	GetMessage() *string
	SetRequestId(v string) *SyncContextResponseBody
	GetRequestId() *string
	SetSuccess(v bool) *SyncContextResponseBody
	GetSuccess() *bool
}

type SyncContextResponseBody struct {
	Code           *string `json:"Code,omitempty" xml:"Code,omitempty"`
	HttpStatusCode *int32  `json:"HttpStatusCode,omitempty" xml:"HttpStatusCode,omitempty"`
	Message        *string `json:"Message,omitempty" xml:"Message,omitempty"`
	RequestId      *string `json:"RequestId,omitempty" xml:"RequestId,omitempty"`
	Success        *bool   `json:"Success,omitempty" xml:"Success,omitempty"`
}

func (s SyncContextResponseBody) String() string {
	return dara.Prettify(s)
}

func (s SyncContextResponseBody) GoString() string {
	return s.String()
}

func (s *SyncContextResponseBody) GetCode() *string {
	return s.Code
}

func (s *SyncContextResponseBody) GetHttpStatusCode() *int32 {
	return s.HttpStatusCode
}

func (s *SyncContextResponseBody) GetMessage() *string {
	return s.Message
}

func (s *SyncContextResponseBody) GetRequestId() *string {
	return s.RequestId
}

func (s *SyncContextResponseBody) GetSuccess() *bool {
	return s.Success
}

func (s *SyncContextResponseBody) SetCode(v string) *SyncContextResponseBody {
	s.Code = &v
	return s
}

func (s *SyncContextResponseBody) SetHttpStatusCode(v int32) *SyncContextResponseBody {
	s.HttpStatusCode = &v
	return s
}

func (s *SyncContextResponseBody) SetMessage(v string) *SyncContextResponseBody {
	s.Message = &v
	return s
}

func (s *SyncContextResponseBody) SetRequestId(v string) *SyncContextResponseBody {
	s.RequestId = &v
	return s
}

func (s *SyncContextResponseBody) SetSuccess(v bool) *SyncContextResponseBody {
	s.Success = &v
	return s
}

func (s *SyncContextResponseBody) Validate() error {
	return dara.Validate(s)
}
