# Create Your First Session

Now let's experience the core features of AgentBay through actual code.

## 🚀 Before You Start (2-minute setup)

If you haven't completed the setup yet, please complete the quick setup steps:

👉 **[Installation and API Key Setup Guide](installation.md)** - Complete SDK installation and API key configuration in 2 minutes

Already done? Great! Let's verify everything works with a quick test.

## 💡 30-Second Quick Verification

Let's first verify everything works with the simplest possible example:

```python
import os
from agentbay import AgentBay

api_key = os.getenv("AGENTBAY_API_KEY")
agent_bay = AgentBay(api_key=api_key)

result = agent_bay.create()
if result.success:
    session = result.session
    cmd_result = session.command.execute_command("echo 'Hello from the cloud!'")
    print(f"✅ Cloud says: {cmd_result.output.strip()}")
    agent_bay.delete(session)
else:
    print(f"❌ Failed: {result.error_message}")

# Expected output:
# ✅ Cloud says: Hello from the cloud!
```

If this works, you're ready to explore more! 🎉

## 🌟 A Practical Example: Cloud Data Processing

Let's do something more useful - process a data file in the cloud:

```python
import os
from agentbay import AgentBay

agent_bay = AgentBay(api_key=os.getenv("AGENTBAY_API_KEY"))
result = agent_bay.create()
session = result.session

try:
    # 1. Create a Python script for data processing
    script_content = '''
import json
import sys

data = {
    "students": [
        {"name": "Alice", "scores": [85, 92, 88]},
        {"name": "Bob", "scores": [78, 85, 80]},
        {"name": "Charlie", "scores": [92, 95, 98]}
    ]
}

results = []
for student in data["students"]:
    avg = sum(student["scores"]) / len(student["scores"])
    results.append({
        "name": student["name"],
        "average": round(avg, 2),
        "grade": "A" if avg >= 90 else "B" if avg >= 80 else "C"
    })

print(json.dumps(results, indent=2))
'''
    
    # 2. Upload script to cloud
    session.file_system.write_file("/tmp/process_data.py", script_content)
    print("✅ Script uploaded to cloud")
    
    # 3. Execute the script in cloud environment
    result = session.command.execute_command("python3 /tmp/process_data.py")
    print(f"\n📊 Processing results:\n{result.output}")
    
    # Expected output:
    # [
    #   {"name": "Alice", "average": 88.33, "grade": "B"},
    #   {"name": "Bob", "average": 81.0, "grade": "B"},
    #   {"name": "Charlie", "average": 95.0, "grade": "A"}
    # ]
    
    print("\n💡 What happened:")
    print("  1. Uploaded Python script to cloud environment")
    print("  2. Executed script with pre-installed Python")
    print("  3. Got results back - all without local setup!")
    
finally:
    agent_bay.delete(session)
    print("\n✅ Session cleaned up")

# Expected output includes JSON formatted student grades
```

## 💡 What You Learned

**The AgentBay Workflow:**
1. **Create** - Get a fresh cloud environment
2. **Use** - Execute commands, upload/download files
3. **Cleanup** - Delete session to free resources

**Key Concepts:**
- `agent_bay.create()` - Creates a new cloud session
- `session.command.execute_command()` - Runs commands in the cloud
- `session.file_system.write_file()` - Uploads files to cloud
- `agent_bay.delete(session)` - Cleans up when done

## 🚀 Next Steps

Now that you've created your first session, explore more capabilities:

**Learn Core Features:**
- 📝 **[Command Execution](../guides/codespace/code-execution.md)** - Run shell commands and code
- 📁 **[File Operations](../guides/common-features/basics/file-operations.md)** - Upload, download, and manage files
- 🔧 **[Session Management](../guides/common-features/basics/session-management.md)** - Advanced session patterns and best practices

**Explore Use Cases:**
- 🌐 **[Browser Automation](../guides/computer-use/computer-ui-automation.md)** - Web scraping and testing
- 📱 **[Mobile Testing](../guides/mobile-use/mobile-ui-automation.md)** - Android app automation
- 💻 **[Code Development](../guides/codespace/code-execution.md)** - Cloud development environment

**Ready to build something amazing?** Check out the [Feature Guides](../guides/README.md) to explore all capabilities! 🚀
