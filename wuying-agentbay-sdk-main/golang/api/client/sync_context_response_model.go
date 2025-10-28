// This file is auto-generated, don't edit it. Thanks.
package client

import (
	"github.com/alibabacloud-go/tea/dara"
)

type iSyncContextResponse interface {
	dara.Model
	String() string
	GoString() string
	SetHeaders(v map[string]*string) *SyncContextResponse
	GetHeaders() map[string]*string
	SetStatusCode(v int32) *SyncContextResponse
	GetStatusCode() *int32
	SetBody(v *SyncContextResponseBody) *SyncContextResponse
	GetBody() *SyncContextResponseBody
}

type SyncContextResponse struct {
	Headers    map[string]*string       `json:"headers,omitempty" xml:"headers,omitempty"`
	StatusCode *int32                   `json:"statusCode,omitempty" xml:"statusCode,omitempty"`
	Body       *SyncContextResponseBody `json:"body,omitempty" xml:"body,omitempty"`
}

func (s SyncContextResponse) String() string {
	return dara.Prettify(s)
}

func (s SyncContextResponse) GoString() string {
	return s.String()
}

func (s *SyncContextResponse) GetHeaders() map[string]*string {
	return s.Headers
}

func (s *SyncContextResponse) GetStatusCode() *int32 {
	return s.StatusCode
}

func (s *SyncContextResponse) GetBody() *SyncContextResponseBody {
	return s.Body
}

func (s *SyncContextResponse) SetHeaders(v map[string]*string) *SyncContextResponse {
	s.Headers = v
	return s
}

func (s *SyncContextResponse) SetStatusCode(v int32) *SyncContextResponse {
	s.StatusCode = &v
	return s
}

func (s *SyncContextResponse) SetBody(v *SyncContextResponseBody) *SyncContextResponse {
	s.Body = v
	return s
}

func (s *SyncContextResponse) Validate() error {
	return dara.Validate(s)
}
