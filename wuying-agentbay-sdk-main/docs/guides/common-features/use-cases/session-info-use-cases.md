# Session Information Use Cases

This document provides practical examples and use cases for using session information obtained from the `session.info()` API. These examples demonstrate common scenarios for integrating AgentBay sessions with different platforms and systems.

## Overview

The `session.info()` method provides detailed information about a session, including direct browser access URLs and SDK integration credentials. This API serves multiple purposes:

1. **Cloud Environment Access**: Get the `resource_url` to directly access the cloud environment in a web browser with real-time video streaming and full mouse/keyboard control
2. **Session Status Validation**: Check if a session is still active and hasn't been released  
3. **SDK Integration**: Extract authentication credentials for Web SDK (desktop) and Android SDK (mobile) integration

## Use Case 1: Cloud Environment Access via Browser

The most common use case is accessing the cloud environment directly through a web browser using the `resource_url`:

```python
def access_cloud_environment_browser(session):
    """Get cloud environment access URL for browser-based remote control."""
    info_result = session.info()

    if info_result.success:
        info = info_result.data
        resource_url = info.resource_url

        print(f"Cloud environment ready for session: {info.session_id}")
        print(f"Resource URL: {resource_url}")
        print("\n🌐 Copy and paste the Resource URL into any web browser to access the cloud environment")
        print("   Features available:")
        print("   - Real-time video stream of the desktop")
        print("   - Mouse and keyboard interaction capabilities")
        print("   - Full remote desktop experience")

        return {
            "session_id": info.session_id,
            "resource_url": resource_url,
            "access_method": "browser_direct"
        }
    else:
        print(f"Failed to get session info: {info_result.error_message}")
        return None

# Usage
access_info = access_cloud_environment_browser(session)
if access_info:
    print("Cloud environment URL is ready - open it in your browser to start using the remote desktop")
```

## Use Case 2: Android SDK Configuration for Cloud Environment Access

The session information obtained from `session.info()` can be used as configuration parameters for the Alibaba Cloud Android SDK, enabling users to connect to the session's cloud environment through the Android SDK:

```python
def prepare_android_sdk_config(session):
    """Prepare Android SDK configuration for cloud environment connection."""
    info_result = session.info()
    
    if info_result.success:
        info = info_result.data
        
        # Android SDK Config parameters based on Alibaba Cloud Android SDK documentation
        # Reference: https://help.aliyun.com/zh/ecp/android-sdk-of-cloud-phone section 4.1 Config
        # info.resource_id maps to CONFIG_DESKTOP_ID
        # info.ticket maps to CONFIG_CONNECTION_TICKET
        android_config = {
            "CONFIG_DESKTOP_ID": info.resource_id,      # Desktop ID for connection
            "CONFIG_CONNECTION_TICKET": info.ticket,    # Connection ticket for authentication
            "CONFIG_USE_VPC": False,                     # VPC configuration (set based on your network setup)
            "OS_TYPE": "android",                        # OS type for the connection
            "CONFIG_USER": "",                           # User identifier (optional)
            "CONFIG_UUID": ""                            # UUID identifier (optional)
        }
        
        print("Android SDK Configuration:")
        print(f"CONFIG_DESKTOP_ID: {info.resource_id}")
        print(f"CONFIG_CONNECTION_TICKET: {info.ticket[:50]}...")  # Truncated for security
        print(f"CONFIG_USE_VPC: {android_config['CONFIG_USE_VPC']}")
        print(f"OS_TYPE: {android_config['OS_TYPE']}")
        
        return android_config
    else:
        print(f"Failed to prepare Android SDK config: {info_result.error_message}")
        return None

# Usage example for Android SDK integration
android_config = prepare_android_sdk_config(session)
if android_config:
    print("Android SDK configuration ready for StreamView connection")
    
    # Method 1: Using StreamView.start() with mConfigs (reference section 2.2)
    # Map<String, Object> mConfigs = new HashMap<>();
    # mConfigs.put("CONFIG_DESKTOP_ID", android_config.get("CONFIG_DESKTOP_ID"));
    # mConfigs.put("CONFIG_CONNECTION_TICKET", android_config.get("CONFIG_CONNECTION_TICKET"));
    # mConfigs.put("CONFIG_USE_VPC", android_config.get("CONFIG_USE_VPC"));
    # mConfigs.put("OS_TYPE", android_config.get("OS_TYPE"));
    # mConfigs.put("CONFIG_USER", android_config.get("CONFIG_USER"));
    # mConfigs.put("CONFIG_UUID", android_config.get("CONFIG_UUID"));
    # mStreamView.start(mConfigs);
    
    # Method 2: Using IAspEngine with ConnectionConfig (reference section 2.5)
    # ConnectionConfig cc = new ConnectionConfig();
    # cc.id = android_config.get("CONFIG_DESKTOP_ID");
    # cc.connectionTicket = android_config.get("CONFIG_CONNECTION_TICKET");
    # cc.useVPC = android_config.get("CONFIG_USE_VPC");
    # cc.type = android_config.get("OS_TYPE");
    # cc.user = android_config.get("CONFIG_USER");
    # cc.uuid = android_config.get("CONFIG_UUID");
    # engine.start(cc);
```

### Android SDK Integration Notes

- **`info.resource_id`** maps to **`CONFIG_DESKTOP_ID`** - This is the unique identifier for the cloud desktop/resource that the Android client will connect to
- **`info.ticket`** maps to **`CONFIG_CONNECTION_TICKET`** - This is the authentication ticket required to establish a secure connection to the cloud environment
- **`CONFIG_USE_VPC`** - Set to `true` if your cloud environment uses VPC networking, `false` for standard networking
- **`OS_TYPE`** - Specifies the OS type, typically set to "android" for mobile connections
- **`CONFIG_USER`** and **`CONFIG_UUID`** - Optional parameters that can be set based on your specific requirements
- The Android SDK supports two connection methods:
  1. **StreamView.start(mConfigs)** - Direct connection using configuration map (section 2.2)
  2. **IAspEngine with ConnectionConfig** - Multi-StreamView mode for advanced scenarios (section 2.5)
- For detailed Android SDK integration steps, refer to the [Alibaba Cloud Android SDK documentation](https://help.aliyun.com/zh/ecp/android-sdk-of-cloud-phone)

## Use Case 3: Session Status Validation and Health Check

Use `info()` to check if a session is still active and hasn't been released:

```python
def check_session_status(session):
    """Check if session is still active and hasn't been released."""
    try:
        info_result = session.info()

        if info_result.success:
            info = info_result.data
            print(f"✅ Session {info.session_id} is ACTIVE")
            print(f"   Resource ID: {info.resource_id}")
            print(f"   App ID: {info.app_id}")
            print(f"   Resource Type: {info.resource_type}")
            return True
        else:
            print(f"❌ Session status check failed: {info_result.error_message}")
            return False

    except Exception as e:
        print(f"❌ Session has been RELEASED or is inaccessible: {e}")
        return False

def monitor_session_health(session, check_interval=30):
    """Continuously monitor session health."""
    import time

    print(f"Starting health monitoring for session: {session.session_id}")

    while True:
        is_active = check_session_status(session)

        if not is_active:
            print("🚨 Session is no longer active - stopping monitoring")
            break

        print(f"💚 Session health check passed - next check in {check_interval}s")
        time.sleep(check_interval)

# Usage examples
print("=== Session Status Check ===")
if check_session_status(session):
    print("Session is ready for use")
else:
    print("Session needs to be recreated")

# For continuous monitoring (run in background thread)
# import threading
# monitor_thread = threading.Thread(target=monitor_session_health, args=(session, 60))
# monitor_thread.daemon = True
# monitor_thread.start()
```

## Additional Integration Scenarios

### Web SDK Integration

For web-based applications that need to embed cloud environment access:

```python
def prepare_web_sdk_config(session):
    """Prepare configuration for Web SDK integration."""
    info_result = session.info()
    
    if info_result.success:
        info = info_result.data
        
        web_config = {
            "session_id": info.session_id,
            "resource_url": info.resource_url,
            "auth_code": info.auth_code,
            "connection_properties": info.connection_properties
        }
        
        return web_config
    else:
        return None
```

### API Gateway Integration

For scenarios where session access needs to be proxied through an API gateway:

```python
def create_session_proxy_endpoint(session):
    """Create API endpoint configuration for session proxy."""
    info_result = session.info()
    
    if info_result.success:
        info = info_result.data
        
        proxy_config = {
            "endpoint": f"/api/sessions/{info.session_id}/proxy",
            "target_url": info.resource_url,
            "auth_token": info.auth_code,
            "session_metadata": {
                "resource_id": info.resource_id,
                "app_id": info.app_id,
                "resource_type": info.resource_type
            }
        }
        
        return proxy_config
    else:
        return None
```

## Best Practices

1. **Always validate session info results** - Check the `success` field before using session information
2. **Handle authentication securely** - Never log or expose auth codes and tickets in plain text
3. **Implement proper error handling** - Session info calls can fail if sessions are released
4. **Cache session information appropriately** - Avoid excessive info() calls, but refresh when needed
5. **Monitor session lifecycle** - Use periodic health checks for long-running applications
6. **Secure credential transmission** - Use HTTPS/TLS when transmitting session credentials to other systems

## Troubleshooting

### Common Issues

1. **Session info returns null/empty**: Session may have been released or expired
2. **Authentication failures**: Verify auth codes and tickets are correctly transmitted
3. **Connection timeouts**: Check network connectivity and firewall settings
4. **Invalid resource URLs**: Ensure the session is still active before using URLs

### Error Handling

```python
def robust_session_info_handler(session):
    """Robust session info handling with comprehensive error handling."""
    try:
        info_result = session.info()
        
        if info_result.success:
            return info_result.data
        else:
            print(f"Session info failed: {info_result.error_message}")
            # Consider session recreation or fallback logic
            return None
            
    except Exception as e:
        print(f"Session info exception: {e}")
        # Session likely released - implement recovery logic
        return None
```

For more information about session management, see the [Session Management Guide](../guides/common-features/basics/session-management.md).
## 📚 Related Guides

- [Session Management](../basics/session-management.md) - Session lifecycle and configuration
- [Session Link Access](../advanced/session-link-access.md) - Session connectivity

## 🆘 Getting Help

- [GitHub Issues](https://github.com/aliyun/wuying-agentbay-sdk/issues)
- [Documentation Home](../../README.md)
