package agentbay

import (
	"encoding/json"

	"github.com/aliyun/wuying-agentbay-sdk/golang/pkg/agentbay/models"
)

// CreateSessionParams provides a way to configure the parameters for creating a new session
// in the AgentBay cloud environment.
type CreateSessionParams struct {
	// Labels are custom labels for the Session. These can be used for organizing and filtering sessions.
	Labels map[string]string

	// ImageId specifies the image ID to use for the session.
	ImageId string

	// ContextSync is a list of context synchronization configurations.
	// These configurations define how contexts should be synchronized and mounted.
	ContextSync []*ContextSync

	// IsVpc specifies whether to create a VPC-based session. Defaults to false.
	IsVpc bool

	// PolicyId specifies the policy ID to apply when creating the session.
	PolicyId string

	// ExtraConfigs contains extra configuration settings for different session types
	ExtraConfigs *models.ExtraConfigs
}

// NewCreateSessionParams creates a new CreateSessionParams with default values.
func NewCreateSessionParams() *CreateSessionParams {
	return &CreateSessionParams{
		Labels:      make(map[string]string),
		ContextSync: make([]*ContextSync, 0),
	}
}

// WithLabels sets the labels for the session parameters and returns the updated parameters.
func (p *CreateSessionParams) WithLabels(labels map[string]string) *CreateSessionParams {
	p.Labels = labels
	return p
}

// WithImageId sets the image ID for the session parameters and returns the updated parameters.
func (p *CreateSessionParams) WithImageId(imageId string) *CreateSessionParams {
	p.ImageId = imageId
	return p
}

// WithIsVpc sets the VPC flag for the session parameters and returns the updated parameters.
func (p *CreateSessionParams) WithIsVpc(isVpc bool) *CreateSessionParams {
	p.IsVpc = isVpc
	return p
}

// WithPolicyId sets the policy ID for the session parameters and returns the updated parameters.
func (p *CreateSessionParams) WithPolicyId(policyId string) *CreateSessionParams {
	p.PolicyId = policyId
	return p
}

// WithExtraConfigs sets the extra configurations for the session parameters and returns the updated parameters.
func (p *CreateSessionParams) WithExtraConfigs(extraConfigs *models.ExtraConfigs) *CreateSessionParams {
	p.ExtraConfigs = extraConfigs
	return p
}

// GetLabelsJSON returns the labels as a JSON string.
func (p *CreateSessionParams) GetLabelsJSON() (string, error) {
	if len(p.Labels) == 0 {
		return "", nil
	}

	labelsJSON, err := json.Marshal(p.Labels)
	if err != nil {
		return "", err
	}

	return string(labelsJSON), nil
}

// GetExtraConfigsJSON returns the extra configs as a JSON string.
func (p *CreateSessionParams) GetExtraConfigsJSON() (string, error) {
	if p.ExtraConfigs == nil {
		return "", nil
	}

	return p.ExtraConfigs.ToJSON()
}

// AddContextSync adds a context sync configuration to the session parameters.
func (p *CreateSessionParams) AddContextSync(contextID, path string, policy *SyncPolicy) *CreateSessionParams {
	contextSync := &ContextSync{
		ContextID: contextID,
		Path:      path,
		Policy:    policy,
	}
	p.ContextSync = append(p.ContextSync, contextSync)
	return p
}

// AddContextSyncConfig adds a pre-configured context sync to the session parameters.
func (p *CreateSessionParams) AddContextSyncConfig(contextSync *ContextSync) *CreateSessionParams {
	p.ContextSync = append(p.ContextSync, contextSync)
	return p
}

// WithContextSync sets the context sync configurations for the session parameters.
func (p *CreateSessionParams) WithContextSync(contextSyncs []*ContextSync) *CreateSessionParams {
	p.ContextSync = contextSyncs
	return p
}
