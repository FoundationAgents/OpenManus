"""
Modular Configuration System

This package provides organizational structure for configuration classes
while maintaining backward compatibility with the monolithic config.py.

The actual configuration settings are still loaded from app.config,
but this module provides semantic grouping and improved organization.

Structure:
    - llm: LLM provider configuration (OpenAI, Azure, Bedrock, etc.)
    - network: Network and API configuration
    - agent: Agent pool and management configuration
    - guardian: Security and approval workflows
    - monitoring: Monitoring and reliability configuration
    - storage: Database and backup configuration
"""

# Re-export from main config for backward compatibility
from app.config import (
    # LLM Settings
    LLMSettings,
    FallbackEndpointSettings,
    LLMAPISettings,
    # Network
    ProxySettings,
    SearchSettings,
    # Agent Management
    AgentPoolSettings,
    SpecializedPoolConfig,
    PoolManagerSettings,
    # Guardian/Security
    GuardianSettings,
    GuardianValidationSettings,
    ACLSettings,
    # Monitoring
    MonitoringSettings,
    # Storage
    BlackboardSettings,
    # Other
    RunflowSettings,
    InteractionSettings,
    ProjectManagementSettings,
    QualityAssuranceSettings,
    DeploymentSettings,
    config,
)

__all__ = [
    # LLM
    "LLMSettings",
    "FallbackEndpointSettings",
    "LLMAPISettings",
    # Network
    "ProxySettings",
    "SearchSettings",
    # Agent
    "AgentPoolSettings",
    "SpecializedPoolConfig",
    "PoolManagerSettings",
    # Guardian
    "GuardianSettings",
    "GuardianValidationSettings",
    "ACLSettings",
    # Monitoring
    "MonitoringSettings",
    # Storage
    "BlackboardSettings",
    # Other
    "RunflowSettings",
    "InteractionSettings",
    "ProjectManagementSettings",
    "QualityAssuranceSettings",
    "DeploymentSettings",
    "config",
]
