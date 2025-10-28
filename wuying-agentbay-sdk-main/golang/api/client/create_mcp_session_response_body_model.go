// This file is auto-generated, don't edit it. Thanks.
package client

import (
	"github.com/alibabacloud-go/tea/dara"
)

type iCreateMcpSessionResponseBody interface {
	dara.Model
	String() string
	GoString() string
	SetCode(v string) *CreateMcpSessionResponseBody
	GetCode() *string
	SetData(v *CreateMcpSessionResponseBodyData) *CreateMcpSessionResponseBody
	GetData() *CreateMcpSessionResponseBodyData
	SetHttpStatusCode(v int32) *CreateMcpSessionResponseBody
	GetHttpStatusCode() *int32
	SetMessage(v string) *CreateMcpSessionResponseBody
	GetMessage() *string
	SetRequestId(v string) *CreateMcpSessionResponseBody
	GetRequestId() *string
	SetSuccess(v bool) *CreateMcpSessionResponseBody
	GetSuccess() *bool
}

type CreateMcpSessionResponseBody struct {
	Code           *string                           `json:"Code,omitempty" xml:"Code,omitempty"`
	Data           *CreateMcpSessionResponseBodyData `json:"Data,omitempty" xml:"Data,omitempty" type:"Struct"`
	HttpStatusCode *int32                            `json:"HttpStatusCode,omitempty" xml:"HttpStatusCode,omitempty"`
	Message        *string                           `json:"Message,omitempty" xml:"Message,omitempty"`
	RequestId      *string                           `json:"RequestId,omitempty" xml:"RequestId,omitempty"`
	Success        *bool                             `json:"Success,omitempty" xml:"Success,omitempty"`
}

func (s CreateMcpSessionResponseBody) String() string {
	return dara.Prettify(s)
}

func (s CreateMcpSessionResponseBody) GoString() string {
	return s.String()
}

func (s *CreateMcpSessionResponseBody) GetCode() *string {
	return s.Code
}

func (s *CreateMcpSessionResponseBody) GetData() *CreateMcpSessionResponseBodyData {
	return s.Data
}

func (s *CreateMcpSessionResponseBody) GetHttpStatusCode() *int32 {
	return s.HttpStatusCode
}

func (s *CreateMcpSessionResponseBody) GetMessage() *string {
	return s.Message
}

func (s *CreateMcpSessionResponseBody) GetRequestId() *string {
	return s.RequestId
}

func (s *CreateMcpSessionResponseBody) GetSuccess() *bool {
	return s.Success
}

func (s *CreateMcpSessionResponseBody) SetCode(v string) *CreateMcpSessionResponseBody {
	s.Code = &v
	return s
}

func (s *CreateMcpSessionResponseBody) SetData(v *CreateMcpSessionResponseBodyData) *CreateMcpSessionResponseBody {
	s.Data = v
	return s
}

func (s *CreateMcpSessionResponseBody) SetHttpStatusCode(v int32) *CreateMcpSessionResponseBody {
	s.HttpStatusCode = &v
	return s
}

func (s *CreateMcpSessionResponseBody) SetMessage(v string) *CreateMcpSessionResponseBody {
	s.Message = &v
	return s
}

func (s *CreateMcpSessionResponseBody) SetRequestId(v string) *CreateMcpSessionResponseBody {
	s.RequestId = &v
	return s
}

func (s *CreateMcpSessionResponseBody) SetSuccess(v bool) *CreateMcpSessionResponseBody {
	s.Success = &v
	return s
}

func (s *CreateMcpSessionResponseBody) Validate() error {
	return dara.Validate(s)
}

type CreateMcpSessionResponseBodyData struct {
	AppInstanceId      *string `json:"AppInstanceId,omitempty" xml:"AppInstanceId,omitempty"`
	ErrMsg             *string `json:"ErrMsg,omitempty" xml:"ErrMsg,omitempty"`
	HttpPort           *string `json:"HttpPort,omitempty" xml:"HttpPort,omitempty"`
	NetworkInterfaceIp *string `json:"NetworkInterfaceIp,omitempty" xml:"NetworkInterfaceIp,omitempty"`
	ResourceId         *string `json:"ResourceId,omitempty" xml:"ResourceId,omitempty"`
	ResourceUrl        *string `json:"ResourceUrl,omitempty" xml:"ResourceUrl,omitempty"`
	SessionId          *string `json:"SessionId,omitempty" xml:"SessionId,omitempty"`
	Success            *bool   `json:"Success,omitempty" xml:"Success,omitempty"`
	Token              *string `json:"Token,omitempty" xml:"Token,omitempty"`
	VpcResource        *bool   `json:"VpcResource,omitempty" xml:"VpcResource,omitempty"`
}

func (s CreateMcpSessionResponseBodyData) String() string {
	return dara.Prettify(s)
}

func (s CreateMcpSessionResponseBodyData) GoString() string {
	return s.String()
}

func (s *CreateMcpSessionResponseBodyData) GetAppInstanceId() *string {
	return s.AppInstanceId
}

func (s *CreateMcpSessionResponseBodyData) GetErrMsg() *string {
	return s.ErrMsg
}

func (s *CreateMcpSessionResponseBodyData) GetResourceId() *string {
	return s.ResourceId
}

func (s *CreateMcpSessionResponseBodyData) GetResourceUrl() *string {
	return s.ResourceUrl
}

func (s *CreateMcpSessionResponseBodyData) GetSessionId() *string {
	return s.SessionId
}

func (s *CreateMcpSessionResponseBodyData) GetSuccess() *bool {
	return s.Success
}

func (s *CreateMcpSessionResponseBodyData) GetHttpPort() *string {
	return s.HttpPort
}

func (s *CreateMcpSessionResponseBodyData) GetNetworkInterfaceIp() *string {
	return s.NetworkInterfaceIp
}

func (s *CreateMcpSessionResponseBodyData) GetToken() *string {
	return s.Token
}

func (s *CreateMcpSessionResponseBodyData) GetVpcResource() *bool {
	return s.VpcResource
}

func (s *CreateMcpSessionResponseBodyData) SetAppInstanceId(v string) *CreateMcpSessionResponseBodyData {
	s.AppInstanceId = &v
	return s
}

func (s *CreateMcpSessionResponseBodyData) SetErrMsg(v string) *CreateMcpSessionResponseBodyData {
	s.ErrMsg = &v
	return s
}

func (s *CreateMcpSessionResponseBodyData) SetResourceId(v string) *CreateMcpSessionResponseBodyData {
	s.ResourceId = &v
	return s
}

func (s *CreateMcpSessionResponseBodyData) SetResourceUrl(v string) *CreateMcpSessionResponseBodyData {
	s.ResourceUrl = &v
	return s
}

func (s *CreateMcpSessionResponseBodyData) SetSessionId(v string) *CreateMcpSessionResponseBodyData {
	s.SessionId = &v
	return s
}

func (s *CreateMcpSessionResponseBodyData) SetSuccess(v bool) *CreateMcpSessionResponseBodyData {
	s.Success = &v
	return s
}

func (s *CreateMcpSessionResponseBodyData) SetHttpPort(v string) *CreateMcpSessionResponseBodyData {
	s.HttpPort = &v
	return s
}

func (s *CreateMcpSessionResponseBodyData) SetNetworkInterfaceIp(v string) *CreateMcpSessionResponseBodyData {
	s.NetworkInterfaceIp = &v
	return s
}

func (s *CreateMcpSessionResponseBodyData) SetToken(v string) *CreateMcpSessionResponseBodyData {
	s.Token = &v
	return s
}

func (s *CreateMcpSessionResponseBodyData) SetVpcResource(v bool) *CreateMcpSessionResponseBodyData {
	s.VpcResource = &v
	return s
}

func (s *CreateMcpSessionResponseBodyData) Validate() error {
	return dara.Validate(s)
}
