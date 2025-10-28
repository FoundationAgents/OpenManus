// This file is auto-generated, don't edit it. Thanks.
package client

import (
	"github.com/alibabacloud-go/tea/dara"
)

type iGetMcpResourceResponseBody interface {
	dara.Model
	String() string
	GoString() string
	SetCode(v string) *GetMcpResourceResponseBody
	GetCode() *string
	SetData(v *GetMcpResourceResponseBodyData) *GetMcpResourceResponseBody
	GetData() *GetMcpResourceResponseBodyData
	SetHttpStatusCode(v int32) *GetMcpResourceResponseBody
	GetHttpStatusCode() *int32
	SetMessage(v string) *GetMcpResourceResponseBody
	GetMessage() *string
	SetRequestId(v string) *GetMcpResourceResponseBody
	GetRequestId() *string
	SetSuccess(v bool) *GetMcpResourceResponseBody
	GetSuccess() *bool
}

type GetMcpResourceResponseBody struct {
	Code           *string                         `json:"Code,omitempty" xml:"Code,omitempty"`
	Data           *GetMcpResourceResponseBodyData `json:"Data,omitempty" xml:"Data,omitempty" type:"Struct"`
	HttpStatusCode *int32                          `json:"HttpStatusCode,omitempty" xml:"HttpStatusCode,omitempty"`
	Message        *string                         `json:"Message,omitempty" xml:"Message,omitempty"`
	RequestId      *string                         `json:"RequestId,omitempty" xml:"RequestId,omitempty"`
	Success        *bool                           `json:"Success,omitempty" xml:"Success,omitempty"`
}

func (s GetMcpResourceResponseBody) String() string {
	return dara.Prettify(s)
}

func (s GetMcpResourceResponseBody) GoString() string {
	return s.String()
}

func (s *GetMcpResourceResponseBody) GetCode() *string {
	return s.Code
}

func (s *GetMcpResourceResponseBody) GetData() *GetMcpResourceResponseBodyData {
	return s.Data
}

func (s *GetMcpResourceResponseBody) GetHttpStatusCode() *int32 {
	return s.HttpStatusCode
}

func (s *GetMcpResourceResponseBody) GetMessage() *string {
	return s.Message
}

func (s *GetMcpResourceResponseBody) GetRequestId() *string {
	return s.RequestId
}

func (s *GetMcpResourceResponseBody) GetSuccess() *bool {
	return s.Success
}

func (s *GetMcpResourceResponseBody) SetCode(v string) *GetMcpResourceResponseBody {
	s.Code = &v
	return s
}

func (s *GetMcpResourceResponseBody) SetData(v *GetMcpResourceResponseBodyData) *GetMcpResourceResponseBody {
	s.Data = v
	return s
}

func (s *GetMcpResourceResponseBody) SetHttpStatusCode(v int32) *GetMcpResourceResponseBody {
	s.HttpStatusCode = &v
	return s
}

func (s *GetMcpResourceResponseBody) SetMessage(v string) *GetMcpResourceResponseBody {
	s.Message = &v
	return s
}

func (s *GetMcpResourceResponseBody) SetRequestId(v string) *GetMcpResourceResponseBody {
	s.RequestId = &v
	return s
}

func (s *GetMcpResourceResponseBody) SetSuccess(v bool) *GetMcpResourceResponseBody {
	s.Success = &v
	return s
}

func (s *GetMcpResourceResponseBody) Validate() error {
	return dara.Validate(s)
}

type GetMcpResourceResponseBodyData struct {
	DesktopInfo *GetMcpResourceResponseBodyDataDesktopInfo `json:"DesktopInfo,omitempty" xml:"DesktopInfo,omitempty" type:"Struct"`
	ResourceUrl *string                                    `json:"ResourceUrl,omitempty" xml:"ResourceUrl,omitempty"`
	SessionId   *string                                    `json:"SessionId,omitempty" xml:"SessionId,omitempty"`
}

func (s GetMcpResourceResponseBodyData) String() string {
	return dara.Prettify(s)
}

func (s GetMcpResourceResponseBodyData) GoString() string {
	return s.String()
}

func (s *GetMcpResourceResponseBodyData) GetDesktopInfo() *GetMcpResourceResponseBodyDataDesktopInfo {
	return s.DesktopInfo
}

func (s *GetMcpResourceResponseBodyData) GetResourceUrl() *string {
	return s.ResourceUrl
}

func (s *GetMcpResourceResponseBodyData) GetSessionId() *string {
	return s.SessionId
}

func (s *GetMcpResourceResponseBodyData) SetDesktopInfo(v *GetMcpResourceResponseBodyDataDesktopInfo) *GetMcpResourceResponseBodyData {
	s.DesktopInfo = v
	return s
}

func (s *GetMcpResourceResponseBodyData) SetResourceUrl(v string) *GetMcpResourceResponseBodyData {
	s.ResourceUrl = &v
	return s
}

func (s *GetMcpResourceResponseBodyData) SetSessionId(v string) *GetMcpResourceResponseBodyData {
	s.SessionId = &v
	return s
}

func (s *GetMcpResourceResponseBodyData) Validate() error {
	return dara.Validate(s)
}

type GetMcpResourceResponseBodyDataDesktopInfo struct {
	AppId                *string `json:"AppId,omitempty" xml:"AppId,omitempty"`
	AuthCode             *string `json:"AuthCode,omitempty" xml:"AuthCode,omitempty"`
	ConnectionProperties *string `json:"ConnectionProperties,omitempty" xml:"ConnectionProperties,omitempty"`
	ResourceId           *string `json:"ResourceId,omitempty" xml:"ResourceId,omitempty"`
	ResourceType         *string `json:"ResourceType,omitempty" xml:"ResourceType,omitempty"`
	Ticket               *string `json:"Ticket,omitempty" xml:"Ticket,omitempty"`
}

func (s GetMcpResourceResponseBodyDataDesktopInfo) String() string {
	return dara.Prettify(s)
}

func (s GetMcpResourceResponseBodyDataDesktopInfo) GoString() string {
	return s.String()
}

func (s *GetMcpResourceResponseBodyDataDesktopInfo) GetAppId() *string {
	return s.AppId
}

func (s *GetMcpResourceResponseBodyDataDesktopInfo) GetAuthCode() *string {
	return s.AuthCode
}

func (s *GetMcpResourceResponseBodyDataDesktopInfo) GetConnectionProperties() *string {
	return s.ConnectionProperties
}

func (s *GetMcpResourceResponseBodyDataDesktopInfo) GetResourceId() *string {
	return s.ResourceId
}

func (s *GetMcpResourceResponseBodyDataDesktopInfo) GetResourceType() *string {
	return s.ResourceType
}

func (s *GetMcpResourceResponseBodyDataDesktopInfo) GetTicket() *string {
	return s.Ticket
}

func (s *GetMcpResourceResponseBodyDataDesktopInfo) SetAppId(v string) *GetMcpResourceResponseBodyDataDesktopInfo {
	s.AppId = &v
	return s
}

func (s *GetMcpResourceResponseBodyDataDesktopInfo) SetAuthCode(v string) *GetMcpResourceResponseBodyDataDesktopInfo {
	s.AuthCode = &v
	return s
}

func (s *GetMcpResourceResponseBodyDataDesktopInfo) SetConnectionProperties(v string) *GetMcpResourceResponseBodyDataDesktopInfo {
	s.ConnectionProperties = &v
	return s
}

func (s *GetMcpResourceResponseBodyDataDesktopInfo) SetResourceId(v string) *GetMcpResourceResponseBodyDataDesktopInfo {
	s.ResourceId = &v
	return s
}

func (s *GetMcpResourceResponseBodyDataDesktopInfo) SetResourceType(v string) *GetMcpResourceResponseBodyDataDesktopInfo {
	s.ResourceType = &v
	return s
}

func (s *GetMcpResourceResponseBodyDataDesktopInfo) SetTicket(v string) *GetMcpResourceResponseBodyDataDesktopInfo {
	s.Ticket = &v
	return s
}

func (s *GetMcpResourceResponseBodyDataDesktopInfo) Validate() error {
	return dara.Validate(s)
}
