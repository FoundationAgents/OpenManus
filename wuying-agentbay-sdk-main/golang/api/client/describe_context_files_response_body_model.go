package client

import (
	"github.com/alibabacloud-go/tea/dara"
)

type iDescribeContextFilesResponseBody interface {
	dara.Model
	String() string
	GoString() string
	SetCode(v string) *DescribeContextFilesResponseBody
	GetCode() *string
	SetCount(v int32) *DescribeContextFilesResponseBody
	GetCount() *int32
	SetData(v []*DescribeContextFilesResponseBodyData) *DescribeContextFilesResponseBody
	GetData() []*DescribeContextFilesResponseBodyData
	SetHttpStatusCode(v int32) *DescribeContextFilesResponseBody
	GetHttpStatusCode() *int32
	SetMessage(v string) *DescribeContextFilesResponseBody
	GetMessage() *string
	SetRequestId(v string) *DescribeContextFilesResponseBody
	GetRequestId() *string
	SetSuccess(v bool) *DescribeContextFilesResponseBody
	GetSuccess() *bool
}

type DescribeContextFilesResponseBody struct {
	Code           *string                                 `json:"Code,omitempty" xml:"Code,omitempty"`
	Count          *int32                                  `json:"Count,omitempty" xml:"Count,omitempty"`
	Data           []*DescribeContextFilesResponseBodyData `json:"Data,omitempty" xml:"Data,omitempty" type:"Repeated"`
	HttpStatusCode *int32                                  `json:"HttpStatusCode,omitempty" xml:"HttpStatusCode,omitempty"`
	Message        *string                                 `json:"Message,omitempty" xml:"Message,omitempty"`
	RequestId      *string                                 `json:"RequestId,omitempty" xml:"RequestId,omitempty"`
	Success        *bool                                   `json:"Success,omitempty" xml:"Success,omitempty"`
}

func (s DescribeContextFilesResponseBody) String() string {
	return dara.Prettify(s)
}

func (s DescribeContextFilesResponseBody) GoString() string {
	return s.String()
}

func (s *DescribeContextFilesResponseBody) GetCode() *string {
	return s.Code
}

func (s *DescribeContextFilesResponseBody) GetCount() *int32 {
	return s.Count
}

func (s *DescribeContextFilesResponseBody) GetData() []*DescribeContextFilesResponseBodyData {
	return s.Data
}

func (s *DescribeContextFilesResponseBody) GetHttpStatusCode() *int32 {
	return s.HttpStatusCode
}

func (s *DescribeContextFilesResponseBody) GetMessage() *string {
	return s.Message
}

func (s *DescribeContextFilesResponseBody) GetRequestId() *string {
	return s.RequestId
}

func (s *DescribeContextFilesResponseBody) GetSuccess() *bool {
	return s.Success
}

func (s *DescribeContextFilesResponseBody) SetCode(v string) *DescribeContextFilesResponseBody {
	s.Code = &v
	return s
}

func (s *DescribeContextFilesResponseBody) SetCount(v int32) *DescribeContextFilesResponseBody {
	s.Count = &v
	return s
}

func (s *DescribeContextFilesResponseBody) SetData(v []*DescribeContextFilesResponseBodyData) *DescribeContextFilesResponseBody {
	s.Data = v
	return s
}

func (s *DescribeContextFilesResponseBody) SetHttpStatusCode(v int32) *DescribeContextFilesResponseBody {
	s.HttpStatusCode = &v
	return s
}

func (s *DescribeContextFilesResponseBody) SetMessage(v string) *DescribeContextFilesResponseBody {
	s.Message = &v
	return s
}

func (s *DescribeContextFilesResponseBody) SetRequestId(v string) *DescribeContextFilesResponseBody {
	s.RequestId = &v
	return s
}

func (s *DescribeContextFilesResponseBody) SetSuccess(v bool) *DescribeContextFilesResponseBody {
	s.Success = &v
	return s
}

func (s *DescribeContextFilesResponseBody) Validate() error {
	return dara.Validate(s)
}

type DescribeContextFilesResponseBodyData struct {
	FileId      *string `json:"FileId,omitempty" xml:"FileId,omitempty"`
	FileName    *string `json:"FileName,omitempty" xml:"FileName,omitempty"`
	FilePath    *string `json:"FilePath,omitempty" xml:"FilePath,omitempty"`
	FileType    *string `json:"FileType,omitempty" xml:"FileType,omitempty"`
	GmtCreate   *string `json:"GmtCreate,omitempty" xml:"GmtCreate,omitempty"`
	GmtModified *string `json:"GmtModified,omitempty" xml:"GmtModified,omitempty"`
	Size        *int64  `json:"Size,omitempty" xml:"Size,omitempty"`
	Status      *string `json:"Status,omitempty" xml:"Status,omitempty"`
}

func (s DescribeContextFilesResponseBodyData) String() string {
	return dara.Prettify(s)
}

func (s DescribeContextFilesResponseBodyData) GoString() string {
	return s.String()
}

func (s *DescribeContextFilesResponseBodyData) GetFileId() *string {
	return s.FileId
}

func (s *DescribeContextFilesResponseBodyData) GetFileName() *string {
	return s.FileName
}

func (s *DescribeContextFilesResponseBodyData) GetFilePath() *string {
	return s.FilePath
}

func (s *DescribeContextFilesResponseBodyData) GetFileType() *string {
	return s.FileType
}

func (s *DescribeContextFilesResponseBodyData) GetGmtCreate() *string {
	return s.GmtCreate
}

func (s *DescribeContextFilesResponseBodyData) GetGmtModified() *string {
	return s.GmtModified
}

func (s *DescribeContextFilesResponseBodyData) GetSize() *int64 {
	return s.Size
}

func (s *DescribeContextFilesResponseBodyData) GetStatus() *string {
	return s.Status
}

func (s *DescribeContextFilesResponseBodyData) SetFileId(v string) *DescribeContextFilesResponseBodyData {
	s.FileId = &v
	return s
}

func (s *DescribeContextFilesResponseBodyData) SetFileName(v string) *DescribeContextFilesResponseBodyData {
	s.FileName = &v
	return s
}

func (s *DescribeContextFilesResponseBodyData) SetFilePath(v string) *DescribeContextFilesResponseBodyData {
	s.FilePath = &v
	return s
}

func (s *DescribeContextFilesResponseBodyData) SetFileType(v string) *DescribeContextFilesResponseBodyData {
	s.FileType = &v
	return s
}

func (s *DescribeContextFilesResponseBodyData) SetGmtCreate(v string) *DescribeContextFilesResponseBodyData {
	s.GmtCreate = &v
	return s
}

func (s *DescribeContextFilesResponseBodyData) SetGmtModified(v string) *DescribeContextFilesResponseBodyData {
	s.GmtModified = &v
	return s
}

func (s *DescribeContextFilesResponseBodyData) SetSize(v int64) *DescribeContextFilesResponseBodyData {
	s.Size = &v
	return s
}

func (s *DescribeContextFilesResponseBodyData) SetStatus(v string) *DescribeContextFilesResponseBodyData {
	s.Status = &v
	return s
}

func (s *DescribeContextFilesResponseBodyData) Validate() error {
	return dara.Validate(s)
}
