# VPC Sessions

## Overview

VPC (Virtual Private Cloud) sessions provide a secure communication mechanism where the SDK directly connects to cloud environments within the same VPC after session creation. This ensures that all business data bypasses AgentBay's control plane services, delivering enhanced security for customers.

### Key Security Benefits

- **Direct Communication**: After session creation, the SDK establishes direct connections to cloud environments within the same VPC
- **Data Privacy**: All business data and operations are transmitted directly between SDK and cloud environment, without passing through AgentBay control services
- **Network Isolation**: Complete network isolation through VPC boundaries ensures secure execution of sensitive workloads
- **Compliance Ready**: Meets enterprise security requirements for data sovereignty and regulatory compliance

## How It Works

1. **Session Creation**: When creating a session with `is_vpc=True`, AgentBay provisions a cloud environment within your VPC
2. **Direct Communication**: All operations (file operations, command execution, browser automation, etc.) communicate directly with the VPC environment
3. **Control Plane Bypass**: Business data never traverses AgentBay's control plane, ensuring maximum data privacy

## Creating VPC Sessions

```python
from agentbay import AgentBay, CreateSessionParams

agent_bay = AgentBay(api_key=api_key)

# Create VPC session
vpc_params = CreateSessionParams(is_vpc=True)

result = agent_bay.create(vpc_params)
if result.success:
    vpc_session = result.session
    print(f"VPC session created successfully: {vpc_session.session_id}")
else:
    print(f"VPC session creation failed: {result.error_message}")
agent_bay.delete(vpc_session)
```

## VPC Session Configuration

VPC sessions are created by setting the `is_vpc` parameter to `True` in the `CreateSessionParams`. The actual VPC configuration (VPC ID, subnet ID, security groups, etc.) is managed by the AgentBay platform and does not need to be specified in the SDK.

## Related Resources

- [Session Management Guide](../basics/session-management.md)
- [SDK Configuration](../configuration/sdk-configuration.md)

## 📚 Related Guides

- [Session Management](../basics/session-management.md) - Session lifecycle and configuration
- [Session Link Access](session-link-access.md) - Session connectivity and URL generation
- [Data Persistence](../basics/data-persistence.md) - Persistent data storage

## 🆘 Getting Help

- [GitHub Issues](https://github.com/aliyun/wuying-agentbay-sdk/issues)
- [Documentation Home](../../README.md)
