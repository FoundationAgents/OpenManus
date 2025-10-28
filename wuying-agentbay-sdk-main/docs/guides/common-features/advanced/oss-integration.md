# OSS Integration

Object Storage Service (OSS) integration enables file upload and download operations between AgentBay sessions and Alibaba Cloud OSS buckets.

## Overview

The OSS module provides:
- **Authenticated Operations**: Upload/download files using OSS credentials
- **Anonymous Operations**: Upload/download files using presigned URLs
- **Session-scoped**: All OSS operations are executed within a cloud session environment

## Prerequisites

Before using OSS operations, you need:
1. An active AgentBay session (preferably `code_latest` image)
2. Alibaba Cloud OSS credentials (Access Key ID and Secret)
3. An OSS bucket (for authenticated operations)

## Basic Workflow

### 1. Initialize OSS Environment

Before performing any OSS operations, you must initialize the OSS environment with your credentials:

```python
from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams

agent_bay = AgentBay(api_key="your-agentbay-api-key")

params = CreateSessionParams(image_id="code_latest")
result = agent_bay.create(params)
session = result.session

init_result = session.oss.env_init(
    access_key_id="your-oss-access-key-id",
    access_key_secret="your-oss-access-key-secret",
    securityToken="optional-security-token",  # Optional: for temporary credentials
    endpoint="https://oss-cn-hangzhou.aliyuncs.com",  # Optional: defaults to OSS endpoint
    region="cn-hangzhou"  # Optional: defaults to OSS region
)

if init_result.success:
    print(f"OSS environment initialized successfully")
    print(f"Request ID: {init_result.request_id}")
else:
    print(f"Failed to initialize OSS: {init_result.error_message}")
```

**Parameters:**
- `access_key_id` (required): Your Alibaba Cloud Access Key ID
- `access_key_secret` (required): Your Alibaba Cloud Access Key Secret
- `securityToken` (optional): Security token for temporary credentials (STS)
- `endpoint` (optional): OSS service endpoint (e.g., `https://oss-cn-hangzhou.aliyuncs.com`)
- `region` (optional): OSS region (e.g., `cn-hangzhou`)

**Returns:**
- `OSSClientResult` with fields:
  - `success` (bool): Whether initialization succeeded
  - `request_id` (str): Unique request identifier
  - `client_config` (dict): OSS client configuration details
  - `error_message` (str): Error description if failed

### 2. Upload Files to OSS

After initialization, upload files from the session to your OSS bucket:

```python
upload_result = session.oss.upload(
    bucket="my-bucket-name",
    object="data/report.pdf",  # Object key in OSS
    path="/home/guest/report.pdf"  # Local path in session
)

if upload_result.success:
    print(f"File uploaded successfully: {upload_result.content}")
    print(f"Request ID: {upload_result.request_id}")
else:
    print(f"Upload failed: {upload_result.error_message}")
```

**Parameters:**
- `bucket` (str): OSS bucket name
- `object` (str): Object key/path in OSS (e.g., `folder/file.txt`)
- `path` (str): Local file path in the session to upload

**Returns:**
- `OSSUploadResult` with fields:
  - `success` (bool): Whether upload succeeded
  - `request_id` (str): Unique request identifier
  - `content` (str): Upload result message
  - `error_message` (str): Error description if failed

### 3. Download Files from OSS

Download files from your OSS bucket to the session:

```python
download_result = session.oss.download(
    bucket="my-bucket-name",
    object="data/report.pdf",  # Object key in OSS
    path="/home/guest/downloaded_report.pdf"  # Local path to save
)

if download_result.success:
    print(f"File downloaded successfully: {download_result.content}")
    print(f"Request ID: {download_result.request_id}")
    
    file_info = session.file_system.get_file_info("/home/guest/downloaded_report.pdf")
    if file_info.success:
        print(f"Downloaded file size: {file_info.size} bytes")
else:
    print(f"Download failed: {download_result.error_message}")
```

**Parameters:**
- `bucket` (str): OSS bucket name
- `object` (str): Object key/path in OSS
- `path` (str): Local file path in the session to save the downloaded file

**Returns:**
- `OSSDownloadResult` with fields:
  - `success` (bool): Whether download succeeded
  - `request_id` (str): Unique request identifier
  - `content` (str): Download result message
  - `error_message` (str): Error description if failed

## Anonymous Operations

Anonymous operations allow uploading/downloading files using presigned URLs or public URLs without requiring OSS credential initialization (`env_init()`).

### Upload Anonymously

Upload a file to a presigned upload URL:

```python
upload_result = session.oss.upload_anonymous(
    url="https://example.com/upload/file.txt",  # Presigned upload URL
    path="/home/guest/file.txt"  # Local file to upload
)

if upload_result.success:
    print(f"Anonymous upload successful: {upload_result.content}")
else:
    print(f"Anonymous upload failed: {upload_result.error_message}")
```

**Parameters:**
- `url` (str): HTTP/HTTPS URL to upload the file to (e.g., presigned OSS upload URL)
- `path` (str): Local file path in the session

**Returns:** Same as `upload()` - `OSSUploadResult`

### Download Anonymously

Download a file from a public URL or presigned download URL:

```python
download_result = session.oss.download_anonymous(
    url="https://example.com/files/document.pdf",  # Public or presigned URL
    path="/home/guest/document.pdf"  # Local path to save
)

if download_result.success:
    print(f"Anonymous download successful: {download_result.content}")
else:
    print(f"Anonymous download failed: {download_result.error_message}")
```

**Parameters:**
- `url` (str): HTTP/HTTPS URL to download the file from
- `path` (str): Local file path in the session to save the downloaded file

**Returns:** Same as `download()` - `OSSDownloadResult`

## Complete Example

Here's a complete workflow demonstrating OSS integration:

```python
from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams

agent_bay = AgentBay(api_key="your-agentbay-api-key")

params = CreateSessionParams(image_id="code_latest")
result = agent_bay.create(params)

if not result.success:
    print(f"Failed to create session: {result.error_message}")
    exit(1)

session = result.session

try:
    init_result = session.oss.env_init(
        access_key_id="your-oss-access-key-id",
        access_key_secret="your-oss-access-key-secret",
        endpoint="https://oss-cn-hangzhou.aliyuncs.com",
        region="cn-hangzhou"
    )
    
    if not init_result.success:
        print(f"Failed to initialize OSS: {init_result.error_message}")
        exit(1)
    
    print("✓ OSS environment initialized")
    
    session.file_system.write_file(
        path="/home/guest/data.txt",
        content="Hello from AgentBay!",
        mode="overwrite"
    )
    print("✓ Created local file")
    
    upload_result = session.oss.upload(
        bucket="my-bucket",
        object="agentbay/data.txt",
        path="/home/guest/data.txt"
    )
    
    if upload_result.success:
        print(f"✓ File uploaded to OSS: {upload_result.content}")
    else:
        print(f"✗ Upload failed: {upload_result.error_message}")
    
    download_result = session.oss.download(
        bucket="my-bucket",
        object="agentbay/data.txt",
        path="/home/guest/downloaded_data.txt"
    )
    
    if download_result.success:
        print(f"✓ File downloaded from OSS: {download_result.content}")
        
        content_result = session.file_system.read_file("/home/guest/downloaded_data.txt")
        if content_result.success:
            print(f"✓ File content: {content_result.content}")
    else:
        print(f"✗ Download failed: {download_result.error_message}")

finally:
    agent_bay.delete(session)
    print("✓ Session deleted")
```

## Error Handling

All OSS operations return result objects with `success` field and `error_message` field. Always check these fields:

```python
result = session.oss.upload(bucket="my-bucket", object="file.txt", path="/tmp/file.txt")

if result.success:
    print(f"Success: {result.content}")
else:
    print(f"Error: {result.error_message}")
```

**Common Error Scenarios:**

1. **Authentication Errors**
   ```
   Error: The OSS Access Key Id you provided does not exist in our records.
   ```
   - Solution: Verify your Access Key ID and Secret

2. **Upload/Download Failures**
   - Check error_message field in result object for specific error details
   - Verify bucket name, object key, and file paths
   - Ensure OSS credentials have appropriate permissions
   - For authenticated operations, verify `env_init()` was called successfully

## Use Cases

### 1. Data Backup

Upload session data to OSS for long-term storage:

```python
import time

session.file_system.create_directory("/home/guest/backup")

json_data = '{"key": "value"}'
session.file_system.write_file("/home/guest/backup/data.json", json_data, "overwrite")

timestamp = int(time.time())
upload_result = session.oss.upload(
    bucket="backup-bucket",
    object=f"backups/{timestamp}/data.json",
    path="/home/guest/backup/data.json"
)
```

### 2. Data Processing

Download data from OSS, process it, and upload results:

```python
session.oss.download(
    bucket="input-bucket",
    object="raw/data.csv",
    path="/home/guest/input.csv"
)

result = session.code.run_code(
    language="python",
    code="""
with open('/home/guest/input.csv', 'r') as f:
    lines = f.readlines()
    
processed_lines = [line.upper() for line in lines]

with open('/home/guest/output.csv', 'w') as f:
    f.writelines(processed_lines)
"""
)

session.oss.upload(
    bucket="output-bucket",
    object="processed/data.csv",
    path="/home/guest/output.csv"
)
```

### 3. File Distribution

Use anonymous download to access public files:

```python
download_result = session.oss.download_anonymous(
    url="https://public-bucket.oss-cn-hangzhou.aliyuncs.com/dataset.zip",
    path="/home/guest/dataset.zip"
)

session.command.execute_command("unzip /home/guest/dataset.zip -d /home/guest/data/")
```

## Best Practices

1. **Always Initialize First**: Call `env_init()` before any other OSS operations
2. **Handle Errors**: Check `success` field and handle `error_message` appropriately
3. **Use Absolute Paths**: Use absolute paths for file operations (e.g., `/home/guest/file.txt`)
4. **Secure Credentials**: Never hardcode credentials; use environment variables
5. **Clean Up**: Delete sessions after completing OSS operations to avoid charges
6. **Request IDs**: Log `request_id` from results for debugging and support

## Security Considerations

- **Credential Management**: Store OSS credentials securely (environment variables, secrets manager)
- **Temporary Credentials**: Use STS temporary credentials with `securityToken` when possible
- **Bucket Permissions**: Grant minimal required permissions to OSS Access Keys
- **Network Security**: Use HTTPS endpoints for OSS operations
- **Session Cleanup**: Always delete sessions containing sensitive data

## Limitations

1. **Session Requirement**: OSS operations require an active session
2. **Initialization Required**: `env_init()` must be called before upload/download operations
3. **Path Restrictions**: File paths must be within the session filesystem
4. **Image Compatibility**: Works best with `code_latest` image

## Related Documentation

- [Session Management](./session-management.md)
- [File Operations](../basics/file-operations.md)
- [Data Persistence](./data-persistence.md)
- [Command Execution](../basics/command-execution.md)
