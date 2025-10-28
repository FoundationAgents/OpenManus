// This file is auto-generated, don't edit it. Thanks.
package client

import (
	"github.com/alibabacloud-go/tea/dara"
)

type iGetLabelResponseBody interface {
	dara.Model
	String() string
	GoString() string
	SetCode(v string) *GetLabelResponseBody
	GetCode() *string
	SetData(v *GetLabelResponseBodyData) *GetLabelResponseBody
	GetData() *GetLabelResponseBodyData
	SetHttpStatusCode(v int32) *GetLabelResponseBody
	GetHttpStatusCode() *int32
	SetMaxResults(v int32) *GetLabelResponseBody
	GetMaxResults() *int32
	SetMessage(v string) *GetLabelResponseBody
	GetMessage() *string
	SetNextToken(v string) *GetLabelResponseBody
	GetNextToken() *string
	SetRequestId(v string) *GetLabelResponseBody
	GetRequestId() *string
	SetSuccess(v bool) *GetLabelResponseBody
	GetSuccess() *bool
	SetTotalCount(v int32) *GetLabelResponseBody
	GetTotalCount() *int32
}

type GetLabelResponseBody struct {
	Code           *string                   `json:"Code,omitempty" xml:"Code,omitempty"`
	Data           *GetLabelResponseBodyData `json:"Data,omitempty" xml:"Data,omitempty" type:"Struct"`
	HttpStatusCode *int32                    `json:"HttpStatusCode,omitempty" xml:"HttpStatusCode,omitempty"`
	MaxResults     *int32                    `json:"MaxResults,omitempty" xml:"MaxResults,omitempty"`
	Message        *string                   `json:"Message,omitempty" xml:"Message,omitempty"`
	NextToken      *string                   `json:"NextToken,omitempty" xml:"NextToken,omitempty"`
	RequestId      *string                   `json:"RequestId,omitempty" xml:"RequestId,omitempty"`
	Success        *bool                     `json:"Success,omitempty" xml:"Success,omitempty"`
	TotalCount     *int32                    `json:"TotalCount,omitempty" xml:"TotalCount,omitempty"`
}

func (s GetLabelResponseBody) String() string {
	return dara.Prettify(s)
}

func (s GetLabelResponseBody) GoString() string {
	return s.String()
}

func (s *GetLabelResponseBody) GetCode() *string {
	return s.Code
}

func (s *GetLabelResponseBody) GetData() *GetLabelResponseBodyData {
	return s.Data
}

func (s *GetLabelResponseBody) GetHttpStatusCode() *int32 {
	return s.HttpStatusCode
}

func (s *GetLabelResponseBody) GetMaxResults() *int32 {
	return s.MaxResults
}

func (s *GetLabelResponseBody) GetMessage() *string {
	return s.Message
}

func (s *GetLabelResponseBody) GetNextToken() *string {
	return s.NextToken
}

func (s *GetLabelResponseBody) GetRequestId() *string {
	return s.RequestId
}

func (s *GetLabelResponseBody) GetSuccess() *bool {
	return s.Success
}

func (s *GetLabelResponseBody) GetTotalCount() *int32 {
	return s.TotalCount
}

func (s *GetLabelResponseBody) SetCode(v string) *GetLabelResponseBody {
	s.Code = &v
	return s
}

func (s *GetLabelResponseBody) SetData(v *GetLabelResponseBodyData) *GetLabelResponseBody {
	s.Data = v
	return s
}

func (s *GetLabelResponseBody) SetHttpStatusCode(v int32) *GetLabelResponseBody {
	s.HttpStatusCode = &v
	return s
}

func (s *GetLabelResponseBody) SetMaxResults(v int32) *GetLabelResponseBody {
	s.MaxResults = &v
	return s
}

func (s *GetLabelResponseBody) SetMessage(v string) *GetLabelResponseBody {
	s.Message = &v
	return s
}

func (s *GetLabelResponseBody) SetNextToken(v string) *GetLabelResponseBody {
	s.NextToken = &v
	return s
}

func (s *GetLabelResponseBody) SetRequestId(v string) *GetLabelResponseBody {
	s.RequestId = &v
	return s
}

func (s *GetLabelResponseBody) SetSuccess(v bool) *GetLabelResponseBody {
	s.Success = &v
	return s
}

func (s *GetLabelResponseBody) SetTotalCount(v int32) *GetLabelResponseBody {
	s.TotalCount = &v
	return s
}

func (s *GetLabelResponseBody) Validate() error {
	return dara.Validate(s)
}

type GetLabelResponseBodyData struct {
	Labels *string `json:"Labels,omitempty" xml:"Labels,omitempty"`
}

func (s GetLabelResponseBodyData) String() string {
	return dara.Prettify(s)
}

func (s GetLabelResponseBodyData) GoString() string {
	return s.String()
}

func (s *GetLabelResponseBodyData) GetLabels() *string {
	return s.Labels
}

func (s *GetLabelResponseBodyData) SetLabels(v string) *GetLabelResponseBodyData {
	s.Labels = &v
	return s
}

func (s *GetLabelResponseBodyData) Validate() error {
	return dara.Validate(s)
}
