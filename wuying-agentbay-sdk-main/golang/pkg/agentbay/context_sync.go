package agentbay

import (
	"encoding/json"
	"fmt"
	"regexp"
)

// UploadStrategy defines the upload strategy for context synchronization
type UploadStrategy string

const (
	// UploadBeforeResourceRelease uploads files before resource release
	UploadBeforeResourceRelease UploadStrategy = "UploadBeforeResourceRelease"
)

// DownloadStrategy defines the download strategy for context synchronization
type DownloadStrategy string

const (
	// DownloadAsync downloads files asynchronously
	DownloadAsync DownloadStrategy = "DownloadAsync"
)

// Lifecycle defines the lifecycle options for recycle policy
type Lifecycle string

const (
	// Lifecycle1Day keeps data for 1 day
	Lifecycle1Day Lifecycle = "Lifecycle_1Day"
	// Lifecycle3Days keeps data for 3 days
	Lifecycle3Days Lifecycle = "Lifecycle_3Days"
	// Lifecycle5Days keeps data for 5 days
	Lifecycle5Days Lifecycle = "Lifecycle_5Days"
	// Lifecycle10Days keeps data for 10 days
	Lifecycle10Days Lifecycle = "Lifecycle_10Days"
	// Lifecycle15Days keeps data for 15 days
	Lifecycle15Days Lifecycle = "Lifecycle_15Days"
	// Lifecycle30Days keeps data for 30 days
	Lifecycle30Days Lifecycle = "Lifecycle_30Days"
	// Lifecycle90Days keeps data for 90 days
	Lifecycle90Days Lifecycle = "Lifecycle_90Days"
	// Lifecycle180Days keeps data for 180 days
	Lifecycle180Days Lifecycle = "Lifecycle_180Days"
	// Lifecycle360Days keeps data for 360 days
	Lifecycle360Days Lifecycle = "Lifecycle_360Days"
	// LifecycleForever keeps data permanently (default)
	LifecycleForever Lifecycle = "Lifecycle_Forever"
)

// UploadPolicy defines the upload policy for context synchronization
type UploadPolicy struct {
	// AutoUpload enables automatic upload
	AutoUpload bool `json:"autoUpload"`
	// UploadStrategy defines the upload strategy
	UploadStrategy UploadStrategy `json:"uploadStrategy"`
}

// NewUploadPolicy creates a new upload policy with default values
func NewUploadPolicy() *UploadPolicy {
	return &UploadPolicy{
		AutoUpload:     true,
		UploadStrategy: UploadBeforeResourceRelease,
	}
}

// DownloadPolicy defines the download policy for context synchronization
type DownloadPolicy struct {
	// AutoDownload enables automatic download
	AutoDownload bool `json:"autoDownload"`
	// DownloadStrategy defines the download strategy
	DownloadStrategy DownloadStrategy `json:"downloadStrategy"`
}

// NewDownloadPolicy creates a new download policy with default values
func NewDownloadPolicy() *DownloadPolicy {
	return &DownloadPolicy{
		AutoDownload:     true,
		DownloadStrategy: DownloadAsync,
	}
}

// DeletePolicy defines the delete policy for context synchronization
type DeletePolicy struct {
	// SyncLocalFile enables synchronization of local file deletions
	SyncLocalFile bool `json:"syncLocalFile"`
}

// NewDeletePolicy creates a new delete policy with default values
func NewDeletePolicy() *DeletePolicy {
	return &DeletePolicy{
		SyncLocalFile: true,
	}
}

// ExtractPolicy defines the extract policy for context synchronization
type ExtractPolicy struct {
	// Extract enables file extraction
	Extract bool `json:"extract"`
	// DeleteSrcFile enables deletion of source file after extraction
	DeleteSrcFile bool `json:"deleteSrcFile"`
	// ExtractToCurrentFolder enables extraction to current folder
	ExtractToCurrentFolder bool `json:"extractToCurrentFolder"`
}

// NewExtractPolicy creates a new extract policy with default values
func NewExtractPolicy() *ExtractPolicy {
	return &ExtractPolicy{
		Extract:                true,
		DeleteSrcFile:          true,
		ExtractToCurrentFolder: false,
	}
}

// RecyclePolicy defines the recycle policy for context synchronization
//
// The RecyclePolicy determines how long context data should be retained and which paths
// are subject to the policy.
//
// Lifecycle field determines the data retention period:
//   - Lifecycle1Day: Keep data for 1 day
//   - Lifecycle3Days: Keep data for 3 days
//   - Lifecycle5Days: Keep data for 5 days
//   - Lifecycle10Days: Keep data for 10 days
//   - Lifecycle15Days: Keep data for 15 days
//   - Lifecycle30Days: Keep data for 30 days
//   - Lifecycle90Days: Keep data for 90 days
//   - Lifecycle180Days: Keep data for 180 days
//   - Lifecycle360Days: Keep data for 360 days
//   - LifecycleForever: Keep data permanently (default)
//
// Paths field specifies which directories or files should be subject to the recycle policy:
//   - Must use exact directory/file paths
//   - Wildcard patterns (* ? [ ]) are NOT supported
//   - Empty string "" means apply to all paths in the context
//   - Multiple paths can be specified as a slice
//   - Default: []string{""} (applies to all paths)
type RecyclePolicy struct {
	// Lifecycle defines how long the context data should be retained
	Lifecycle Lifecycle `json:"lifecycle"`
	// Paths specifies which directories or files should be subject to the recycle policy
	Paths []string `json:"paths"`
}

// NewRecyclePolicy creates a new recycle policy with default values
func NewRecyclePolicy() *RecyclePolicy {
	return &RecyclePolicy{
		Lifecycle: LifecycleForever,
		Paths:     []string{""},
	}
}

// isValidLifecycle checks if the given lifecycle value is valid
func isValidLifecycle(lifecycle Lifecycle) bool {
	switch lifecycle {
	case Lifecycle1Day, Lifecycle3Days, Lifecycle5Days, Lifecycle10Days, Lifecycle15Days,
		Lifecycle30Days, Lifecycle90Days, Lifecycle180Days, Lifecycle360Days, LifecycleForever:
		return true
	default:
		return false
	}
}

// Validate validates the RecyclePolicy configuration
func (rp *RecyclePolicy) Validate() error {
	// Validate Lifecycle value
	if !isValidLifecycle(rp.Lifecycle) {
		return fmt.Errorf(
			"invalid lifecycle value: %s. Valid values are: %s, %s, %s, %s, %s, %s, %s, %s, %s, %s",
			rp.Lifecycle,
			Lifecycle1Day, Lifecycle3Days, Lifecycle5Days, Lifecycle10Days, Lifecycle15Days,
			Lifecycle30Days, Lifecycle90Days, Lifecycle180Days, Lifecycle360Days, LifecycleForever,
		)
	}

	// Validate paths don't contain wildcard patterns
	for _, path := range rp.Paths {
		if path != "" && containsWildcard(path) {
			return fmt.Errorf(
				"wildcard patterns are not supported in recycle policy paths. Got: %s. Please use exact directory paths instead",
				path,
			)
		}
	}
	return nil
}

// WhiteList defines the white list configuration
type WhiteList struct {
	// Path is the path to include in the white list
	Path string `json:"path"`
	// ExcludePaths are the paths to exclude from the white list
	ExcludePaths []string `json:"excludePaths,omitempty"`
}

var wildcardPattern = regexp.MustCompile(`[*?\[\]]`)

func containsWildcard(path string) bool {
	return wildcardPattern.MatchString(path)
}

func (wl *WhiteList) Validate() error {
	if containsWildcard(wl.Path) {
		return fmt.Errorf(
			"wildcard patterns are not supported in path. Got: %s. Please use exact directory paths instead",
			wl.Path,
		)
	}

	for _, excludePath := range wl.ExcludePaths {
		if containsWildcard(excludePath) {
			return fmt.Errorf(
				"wildcard patterns are not supported in exclude_paths. Got: %s. Please use exact directory paths instead",
				excludePath,
			)
		}
	}

	return nil
}

// BWList defines the black and white list configuration
type BWList struct {
	// WhiteLists defines the white lists
	WhiteLists []*WhiteList `json:"whiteLists,omitempty"`
}

// SyncPolicy defines the synchronization policy
type SyncPolicy struct {
	// UploadPolicy defines the upload policy
	UploadPolicy *UploadPolicy `json:"uploadPolicy,omitempty"`
	// DownloadPolicy defines the download policy
	DownloadPolicy *DownloadPolicy `json:"downloadPolicy,omitempty"`
	// DeletePolicy defines the delete policy
	DeletePolicy *DeletePolicy `json:"deletePolicy,omitempty"`
	// ExtractPolicy defines the extract policy
	ExtractPolicy *ExtractPolicy `json:"extractPolicy,omitempty"`
	// RecyclePolicy defines the recycle policy
	RecyclePolicy *RecyclePolicy `json:"recyclePolicy,omitempty"`
	// BWList defines the black and white list
	BWList *BWList `json:"bwList,omitempty"`
}

// NewSyncPolicy creates a new sync policy with default values
func NewSyncPolicy() *SyncPolicy {
	return &SyncPolicy{
		UploadPolicy:   NewUploadPolicy(),
		DownloadPolicy: NewDownloadPolicy(),
		DeletePolicy:   NewDeletePolicy(),
		ExtractPolicy:  NewExtractPolicy(),
		RecyclePolicy:  NewRecyclePolicy(),
		BWList: &BWList{
			WhiteLists: []*WhiteList{
				{
					Path:         "",
					ExcludePaths: []string{},
				},
			},
		},
	}
}

// ensureDefaults ensures all policy fields have default values if not provided
func (sp *SyncPolicy) ensureDefaults() {
	if sp.UploadPolicy == nil {
		sp.UploadPolicy = NewUploadPolicy()
	}
	if sp.DownloadPolicy == nil {
		sp.DownloadPolicy = NewDownloadPolicy()
	}
	if sp.DeletePolicy == nil {
		sp.DeletePolicy = NewDeletePolicy()
	}
	if sp.ExtractPolicy == nil {
		sp.ExtractPolicy = NewExtractPolicy()
	}
	if sp.RecyclePolicy == nil {
		sp.RecyclePolicy = NewRecyclePolicy()
	}
	if sp.BWList == nil {
		sp.BWList = &BWList{
			WhiteLists: []*WhiteList{
				{
					Path:         "",
					ExcludePaths: []string{},
				},
			},
		}
	}
}

// MarshalJSON ensures all fields have default values before marshaling
func (sp *SyncPolicy) MarshalJSON() ([]byte, error) {
	sp.ensureDefaults()

	// Create a temporary struct to avoid infinite recursion
	type SyncPolicyAlias SyncPolicy
	return json.Marshal((*SyncPolicyAlias)(sp))
}

// ContextSync defines the context synchronization configuration
type ContextSync struct {
	// ContextID is the ID of the context to synchronize
	ContextID string `json:"contextId"`
	// Path is the path where the context should be mounted
	Path string `json:"path"`
	// Policy defines the synchronization policy
	Policy *SyncPolicy `json:"policy,omitempty"`
}

func validateSyncPolicy(policy *SyncPolicy) error {
	if policy == nil {
		return nil
	}

	// Validate RecyclePolicy paths
	if policy.RecyclePolicy != nil {
		if err := policy.RecyclePolicy.Validate(); err != nil {
			return err
		}
	}

	// Validate BWList whitelist paths
	if policy.BWList != nil && policy.BWList.WhiteLists != nil {
		for _, whitelist := range policy.BWList.WhiteLists {
			if err := whitelist.Validate(); err != nil {
				return err
			}
		}
	}

	return nil
}

// NewContextSync creates a new context sync configuration
func NewContextSync(contextID, path string, policy *SyncPolicy) (*ContextSync, error) {
	if err := validateSyncPolicy(policy); err != nil {
		return nil, err
	}

	return &ContextSync{
		ContextID: contextID,
		Path:      path,
		Policy:    policy,
	}, nil
}

// WithPolicy sets the policy and returns the context sync for chaining
func (cs *ContextSync) WithPolicy(policy *SyncPolicy) (*ContextSync, error) {
	if err := validateSyncPolicy(policy); err != nil {
		return nil, err
	}
	cs.Policy = policy
	return cs, nil
}
