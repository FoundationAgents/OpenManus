"""
Basic Extension Management Example

This example demonstrates the fundamental usage of browser extensions with AgentBay SDK.
"""

import os
from agentbay import AgentBay
from agentbay.extension import ExtensionsService
from agentbay.session_params import CreateSessionParams, BrowserContext


def basic_extension_example():
    """Basic extension upload and browser session creation."""
    
    # Initialize AgentBay client
    agent_bay = AgentBay(api_key=os.getenv("AGENTBAY_API_KEY"))
    
    # Initialize extensions service (auto-creates context)
    extensions_service = ExtensionsService(agent_bay)
    
    try:
        print("🚀 Starting basic extension example...")
        
        # Upload extension (replace with your extension path)
        extension_path = "/path/to/your-extension.zip"  # Update this path
        
        if not os.path.exists(extension_path):
            print(f"❌ Extension file not found: {extension_path}")
            print("💡 Please update the extension_path variable with a valid ZIP file")
            return False
        
        # Upload extension to cloud
        print(f"📦 Uploading extension: {extension_path}")
        extension = extensions_service.create(extension_path)
        print(f"✅ Extension uploaded successfully!")
        print(f"   - Name: {extension.name}")
        print(f"   - ID: {extension.id}")
        
        # Create extension option for browser session
        print("🔧 Creating extension configuration...")
        ext_option = extensions_service.create_extension_option([extension.id])
        print(f"✅ Extension option created: {ext_option}")
        
        # Create browser session with extension
        print("🌐 Creating browser session with extension...")
        session_params = CreateSessionParams(
            labels={"purpose": "basic_extension_example", "type": "demo"},
            browser_context=BrowserContext(
                context_id="basic_extension_session",
                auto_upload=True,
                extension_option=ext_option
            )
        )
        
        session_result = agent_bay.create(session_params)
        if not session_result.success:
            print(f"❌ Failed to create session: {session_result.error_message}")
            return False
        
        session = session_result.session
        print(f"✅ Browser session created successfully!")
        print(f"   - Session ID: {session.session_id}")
        print(f"   - Extensions synchronized to: /tmp/extensions/")
        
        # List available extensions in context
        print("\n📋 Listing available extensions:")
        extensions = extensions_service.list()
        for ext in extensions:
            print(f"   - {ext.name} (ID: {ext.id})")
        
        print("\n🎉 Extension example completed successfully!")
        print("💡 The extension is now available in the browser session at /tmp/extensions/")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during extension example: {e}")
        return False
    finally:
        # Clean up resources
        print("\n🧹 Cleaning up resources...")
        extensions_service.cleanup()
        print("✅ Cleanup completed")


def multiple_extensions_example():
    """Example with multiple extensions."""
    
    agent_bay = AgentBay(api_key=os.getenv("AGENTBAY_API_KEY"))
    extensions_service = ExtensionsService(agent_bay, "multi_ext_demo")
    
    try:
        print("🚀 Starting multiple extensions example...")
        
        # List of extension paths (update with your actual extensions)
        extension_paths = [
            "/path/to/extension1.zip",
            "/path/to/extension2.zip",
            "/path/to/extension3.zip"
        ]
        
        # Filter existing files
        existing_paths = [path for path in extension_paths if os.path.exists(path)]
        if not existing_paths:
            print("❌ No extension files found. Please update extension_paths with valid ZIP files")
            return False
        
        print(f"📦 Uploading {len(existing_paths)} extensions...")
        
        # Upload all extensions
        extension_ids = []
        for path in existing_paths:
            ext = extensions_service.create(path)
            extension_ids.append(ext.id)
            print(f"   ✅ {ext.name} uploaded (ID: {ext.id})")
        
        # Create session with all extensions
        print("🔧 Creating configuration for all extensions...")
        ext_option = extensions_service.create_extension_option(extension_ids)
        
        session_params = CreateSessionParams(
            labels={"purpose": "multiple_extensions", "count": str(len(extension_ids))},
            browser_context=BrowserContext(
                context_id="multi_extension_session",
                extension_option=ext_option
            )
        )
        
        print("🌐 Creating browser session...")
        session_result = agent_bay.create(session_params)
        session = session_result.session
        
        print(f"✅ Session created with {len(extension_ids)} extensions!")
        print(f"   - Session ID: {session.session_id}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        extensions_service.cleanup()


if __name__ == "__main__":
    print("AgentBay Extension Examples")
    print("=" * 50)
    
    # Check API key
    if not os.getenv("AGENTBAY_API_KEY"):
        print("❌ Please set AGENTBAY_API_KEY environment variable")
        exit(1)
    
    print("\n1. Basic Extension Example")
    print("-" * 30)
    basic_extension_example()
    
    print("\n2. Multiple Extensions Example")
    print("-" * 30)
    multiple_extensions_example()
    
    print("\n🎯 Examples completed!")
    print("\n💡 Next steps:")
    print("   - Update extension paths with your actual ZIP files")
    print("   - Check extension_development_workflow.py for advanced usage")
    print("   - See browser automation examples for integration patterns")