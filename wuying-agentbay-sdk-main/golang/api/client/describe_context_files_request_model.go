package client

import (
	"github.com/alibabacloud-go/tea/dara"
)

type iDescribeContextFilesRequest interface {
	dara.Model
	String() string
	GoString() string
	SetAuthorization(v string) *DescribeContextFilesRequest
	GetAuthorization() *string
	SetPageNumber(v int32) *DescribeContextFilesRequest
	GetPageNumber() *int32
	SetPageSize(v int32) *DescribeContextFilesRequest
	GetPageSize() *int32
	SetParentFolderPath(v string) *DescribeContextFilesRequest
	GetParentFolderPath() *string
	SetContextId(v string) *DescribeContextFilesRequest
	GetContextId() *string
}

type DescribeContextFilesRequest struct {
	Authorization    *string `json:"Authorization,omitempty" xml:"Authorization,omitempty"`
	PageNumber       *int32  `json:"PageNumber,omitempty" xml:"PageNumber,omitempty"`
	PageSize         *int32  `json:"PageSize,omitempty" xml:"PageSize,omitempty"`
	ParentFolderPath *string `json:"ParentFolderPath,omitempty" xml:"ParentFolderPath,omitempty"`
	ContextId        *string `json:"ContextId,omitempty" xml:"ContextId,omitempty"`
}

func (s DescribeContextFilesRequest) String() string {
	return dara.Prettify(s)
}

func (s DescribeContextFilesRequest) GoString() string {
	return s.String()
}

func (s *DescribeContextFilesRequest) GetAuthorization() *string {
	return s.Authorization
}

func (s *DescribeContextFilesRequest) GetPageNumber() *int32 {
	return s.PageNumber
}

func (s *DescribeContextFilesRequest) GetPageSize() *int32 {
	return s.PageSize
}

func (s *DescribeContextFilesRequest) GetParentFolderPath() *string {
	return s.ParentFolderPath
}

func (s *DescribeContextFilesRequest) GetContextId() *string {
	return s.ContextId
}

func (s *DescribeContextFilesRequest) SetAuthorization(v string) *DescribeContextFilesRequest {
	s.Authorization = &v
	return s
}

func (s *DescribeContextFilesRequest) SetPageNumber(v int32) *DescribeContextFilesRequest {
	s.PageNumber = &v
	return s
}

func (s *DescribeContextFilesRequest) SetPageSize(v int32) *DescribeContextFilesRequest {
	s.PageSize = &v
	return s
}

func (s *DescribeContextFilesRequest) SetParentFolderPath(v string) *DescribeContextFilesRequest {
	s.ParentFolderPath = &v
	return s
}

func (s *DescribeContextFilesRequest) SetContextId(v string) *DescribeContextFilesRequest {
	s.ContextId = &v
	return s
}

func (s *DescribeContextFilesRequest) Validate() error {
	return dara.Validate(s)
}
