package agentbay_test

import (
	"testing"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay"
	"github.com/stretchr/testify/assert"
)

func TestWhiteListValidation_ValidPaths(t *testing.T) {
	tests := []struct {
		name         string
		path         string
		excludePaths []string
	}{
		{
			name:         "path without wildcards",
			path:         "/src",
			excludePaths: nil,
		},
		{
			name:         "path with exclude_paths without wildcards",
			path:         "/src",
			excludePaths: []string{"/node_modules", "/temp"},
		},
		{
			name:         "empty path",
			path:         "",
			excludePaths: nil,
		},
		{
			name:         "empty exclude_paths",
			path:         "/src",
			excludePaths: []string{},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			wl := &agentbay.WhiteList{
				Path:         tt.path,
				ExcludePaths: tt.excludePaths,
			}
			err := wl.Validate()
			assert.NoError(t, err)
		})
	}
}

func TestWhiteListValidation_InvalidPathsWithWildcards(t *testing.T) {
	tests := []struct {
		name        string
		path        string
		expectedErr string
	}{
		{
			name:        "path with asterisk wildcard",
			path:        "/data/*",
			expectedErr: "wildcard patterns are not supported in path. Got: /data/*",
		},
		{
			name:        "path with double asterisk",
			path:        "/logs/**/*.txt",
			expectedErr: "wildcard patterns are not supported in path",
		},
		{
			name:        "path with question mark",
			path:        "/file?.txt",
			expectedErr: "wildcard patterns are not supported in path",
		},
		{
			name:        "path with brackets",
			path:        "/file[0-9].txt",
			expectedErr: "wildcard patterns are not supported in path",
		},
		{
			name:        "glob pattern",
			path:        "*.json",
			expectedErr: "wildcard patterns are not supported in path",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			wl := &agentbay.WhiteList{
				Path: tt.path,
			}
			err := wl.Validate()
			assert.Error(t, err)
			assert.Contains(t, err.Error(), tt.expectedErr)
		})
	}
}

func TestWhiteListValidation_InvalidExcludePathsWithWildcards(t *testing.T) {
	tests := []struct {
		name         string
		excludePaths []string
		expectedErr  string
	}{
		{
			name:         "exclude_paths with asterisk",
			excludePaths: []string{"*.log"},
			expectedErr:  "wildcard patterns are not supported in exclude_paths. Got: *.log",
		},
		{
			name:         "exclude_paths with pattern",
			excludePaths: []string{"/node_modules", "**/*.tmp"},
			expectedErr:  "wildcard patterns are not supported in exclude_paths",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			wl := &agentbay.WhiteList{
				Path:         "/src",
				ExcludePaths: tt.excludePaths,
			}
			err := wl.Validate()
			assert.Error(t, err)
			assert.Contains(t, err.Error(), tt.expectedErr)
		})
	}
}

func TestContextSyncValidation_Constructor(t *testing.T) {
	t.Run("valid policy", func(t *testing.T) {
		policy := &agentbay.SyncPolicy{
			BWList: &agentbay.BWList{
				WhiteLists: []*agentbay.WhiteList{
					{
						Path:         "/src",
						ExcludePaths: []string{"/node_modules"},
					},
				},
			},
		}

		contextSync, err := agentbay.NewContextSync("ctx-123", "/tmp/data", policy)
		assert.NoError(t, err)
		assert.NotNil(t, contextSync)
	})

	t.Run("invalid policy with wildcard in path", func(t *testing.T) {
		policy := &agentbay.SyncPolicy{
			BWList: &agentbay.BWList{
				WhiteLists: []*agentbay.WhiteList{
					{Path: "*.json"},
				},
			},
		}

		contextSync, err := agentbay.NewContextSync("ctx-123", "/tmp/data", policy)
		assert.Error(t, err)
		assert.Nil(t, contextSync)
		assert.Contains(t, err.Error(), "wildcard patterns are not supported in path")
	})

	t.Run("invalid policy with wildcard in exclude_paths", func(t *testing.T) {
		policy := &agentbay.SyncPolicy{
			BWList: &agentbay.BWList{
				WhiteLists: []*agentbay.WhiteList{
					{
						Path:         "/src",
						ExcludePaths: []string{"*.log"},
					},
				},
			},
		}

		contextSync, err := agentbay.NewContextSync("ctx-123", "/tmp/data", policy)
		assert.Error(t, err)
		assert.Nil(t, contextSync)
		assert.Contains(t, err.Error(), "wildcard patterns are not supported in exclude_paths")
	})

	t.Run("nil policy is valid", func(t *testing.T) {
		contextSync, err := agentbay.NewContextSync("ctx-123", "/tmp/data", nil)
		assert.NoError(t, err)
		assert.NotNil(t, contextSync)
	})
}

func TestContextSyncValidation_WithPolicy(t *testing.T) {
	t.Run("valid policy", func(t *testing.T) {
		contextSync, _ := agentbay.NewContextSync("ctx-123", "/tmp/data", nil)

		policy := &agentbay.SyncPolicy{
			BWList: &agentbay.BWList{
				WhiteLists: []*agentbay.WhiteList{
					{
						Path:         "/src",
						ExcludePaths: []string{"/node_modules"},
					},
				},
			},
		}

		result, err := contextSync.WithPolicy(policy)
		assert.NoError(t, err)
		assert.NotNil(t, result)
		assert.Same(t, contextSync, result)
	})

	t.Run("invalid policy", func(t *testing.T) {
		contextSync, _ := agentbay.NewContextSync("ctx-123", "/tmp/data", nil)

		policy := &agentbay.SyncPolicy{
			BWList: &agentbay.BWList{
				WhiteLists: []*agentbay.WhiteList{
					{
						Path:         "/src",
						ExcludePaths: []string{"*.log"},
					},
				},
			},
		}

		result, err := contextSync.WithPolicy(policy)
		assert.Error(t, err)
		assert.Nil(t, result)
		assert.Contains(t, err.Error(), "wildcard patterns are not supported in exclude_paths")
	})
}
