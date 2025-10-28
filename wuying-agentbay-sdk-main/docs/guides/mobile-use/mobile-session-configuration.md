# Mobile Session Configuration

This guide demonstrates how to create mobile sessions with advanced configuration options using the AgentBay SDK. The mobile configuration allows you to control application access and screen resolution settings for mobile environments.

## Table of Contents
- [Overview](#overview)
- [Configuration Options](#configuration-options)
- [Whitelist Configuration](#whitelist-configuration)
- [Blacklist Configuration](#blacklist-configuration)

## Overview

When creating mobile sessions, you can configure advanced settings using the `extra_configs` parameter in `CreateSessionParams`. This allows you to:

- Control application access through whitelist or blacklist rules
- Lock or unlock screen resolution
- Enhance security and testing flexibility

## Configuration Options

The mobile configuration supports the following options:

### Resolution Settings

- **`lock_resolution`** (bool): Controls whether the screen resolution is locked
  - `True`: Locks the resolution to prevent changes
  - `False`: Allows resolution changes for flexible display adaptation

### App Manager Rule

- **`app_manager_rule`** (AppManagerRule): Controls application access
  - **`rule_type`**: Either "White" (whitelist) or "Black" (blacklist)
  - **`app_package_name_list`**: List of package names to allow or block

## Whitelist Configuration

Use whitelists in production environments to ensure only approved applications can be installed and accessed. This provides the highest level of security by explicitly allowing only trusted applications.

### Example: Creating a Session with App Whitelist

```python
from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams
from agentbay.api.models import ExtraConfigs, MobileExtraConfig, AppManagerRule

# Initialize the SDK
agent_bay = AgentBay(api_key="your_api_key")

# Configure mobile app management with whitelist
app_whitelist_rule = AppManagerRule(
    rule_type="White",
    app_package_name_list=[
        "com.example.allowed.app",
        "com.company.trusted.app",
        "com.system.essential.service"
    ]
)

# Configure mobile settings
mobile_config = MobileExtraConfig(
    lock_resolution=True,
    app_manager_rule=app_whitelist_rule
)

# Create extra configs
extra_configs = ExtraConfigs(mobile=mobile_config)

# Create session with mobile configuration
params = CreateSessionParams(
    image_id="mobile_latest",
    labels={"project": "mobile-testing", "environment": "development"},
    extra_configs=extra_configs
)

session_result = agent_bay.create(params)
if session_result.success:
    session = session_result.session
    print(f"Mobile session created with ID: {session.session_id}")
    print("Mobile configuration applied:")
    print("- Resolution locked")
    print("- App whitelist enabled with allowed packages")
else:
    print(f"Failed to create mobile session: {session_result.error_message}")
```

## Blacklist Configuration

Use blacklists in development and testing to block known problematic applications while allowing flexibility for other apps. This approach is useful when you want to prevent access to specific applications without restricting the entire environment.

### Example: Creating a Session with App Blacklist

```python
from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams
from agentbay.api.models import ExtraConfigs, MobileExtraConfig, AppManagerRule

# Initialize the SDK
agent_bay = AgentBay(api_key="your_api_key")

# Configure mobile app management with blacklist
app_blacklist_rule = AppManagerRule(
    rule_type="Black",
    app_package_name_list=[
        "com.malware.suspicious.app",
        "com.unwanted.adware",
        "com.blocked.social.media"
    ]
)

# Configure mobile settings with resolution flexibility
mobile_config = MobileExtraConfig(
    lock_resolution=False,
    app_manager_rule=app_blacklist_rule
)

# Create extra configs
extra_configs = ExtraConfigs(mobile=mobile_config)

# Create session with mobile blacklist configuration
params = CreateSessionParams(
    image_id="mobile_latest",
    labels={"project": "security-testing"},
    extra_configs=extra_configs
)

session_result = agent_bay.create(params)
if session_result.success:
    session = session_result.session
    print(f"Secure mobile session created with ID: {session.session_id}")
    print("Security configuration applied:")
    print("- Resolution unlocked for flexibility")
    print("- App blacklist enabled to block malicious packages")
else:
    print(f"Failed to create mobile session: {session_result.error_message}")
```

## Related Documentation

- [Mobile Application Management](./mobile-application-management.md)
- [Mobile UI Automation](./mobile-ui-automation.md)
- [Session Creation Basics](../common-features/basics/session-management.md)
