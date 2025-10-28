#!/usr/bin/env python3
"""
AgentBay SDK - Automation Features Example

This example demonstrates how to use AgentBay SDK automation features with different images:
- Command execution using linux_latest image
- Code execution using code_latest image  
- Linux UI automation using linux_latest image
- Mobile UI automation using mobile_latest image
"""

import os
import time
from agentbay import AgentBay
from agentbay.session_params import CreateSessionParams

def main():
    """Main function"""
    print("🚀 AgentBay Automation Features Example")
    
    # Initialize AgentBay client
    agent_bay = AgentBay()
    
    try:
        # 1. Command execution example with linux_latest image
        command_execution_example(agent_bay)
        
        # 2. Code execution example with code_latest image
        code_execution_example(agent_bay)
        
        # 3. Linux UI automation example with linux_latest image
        linux_ui_automation_example(agent_bay)
        
        # 4. Mobile UI automation example with mobile_latest image
        mobile_ui_automation_example(agent_bay)
        
    except Exception as e:
        print(f"❌ Example execution failed: {e}")
    
    print("✅ All examples completed")

def command_execution_example(agent_bay):
    """Command execution example using linux_latest image"""
    print("\n💻 === Command Execution Example (linux_latest) ===")
    
    # Create session with linux_latest image
    print("📱 Creating session with linux_latest image...")
    params = CreateSessionParams(image_id="linux_latest")
    session_result = agent_bay.create(params)
    
    if not session_result.success:
        print(f"❌ Session creation failed: {session_result.error_message}")
        return
    
    session = session_result.session
    print(f"✅ Session created successfully: {session.session_id}")
    
    try:
        # Basic command execution
        commands = [
            "whoami",
            "pwd", 
            "ls -la /tmp",
            "df -h",
            "free -h",
            "uname -a"
        ]
        
        for cmd in commands:
            print(f"\n🔄 Executing command: {cmd}")
            result = session.command.execute_command(cmd)
            
            if result.success:
                print(f"✅ Output: {result.output.strip()}")
            else:
                print(f"❌ Command failed: {result.error_message}")
        
        # Command execution with timeout
        print(f"\n🔄 Executing command with timeout...")
        result = session.command.execute_command("sleep 2", timeout_ms=5000)
        if result.success:
            print("✅ Timeout command executed successfully")
        else:
            print(f"❌ Timeout command failed: {result.error_message}")
            
    finally:
        # Clean up session
        print(f"\n🧹 Cleaning up linux session: {session.session_id}")
        agent_bay.delete(session)

def code_execution_example(agent_bay):
    """Code execution example using code_latest image"""
    print("\n🐍 === Code Execution Example (code_latest) ===")
    
    # Create session with code_latest image
    print("📱 Creating session with code_latest image...")
    params = CreateSessionParams(image_id="code_latest")
    session_result = agent_bay.create(params)
    
    if not session_result.success:
        print(f"❌ Session creation failed: {session_result.error_message}")
        return
    
    session = session_result.session
    print(f"✅ Session created successfully: {session.session_id}")
    
    try:
        # Python code execution
        python_code = """
import sys
import os
import json
from datetime import datetime

# System information
system_info = {
    "python_version": sys.version,
    "current_directory": os.getcwd(),
    "timestamp": datetime.now().isoformat(),
    "environment_vars": len(os.environ)
}

print("Python code execution successful!")
print(f"System info: {json.dumps(system_info, indent=2)}")

# Simple calculation
numbers = list(range(1, 11))
total = sum(numbers)
print(f"Sum of 1 to 10: {total}")
"""
        
        print("🔄 Executing Python code...")
        result = session.code.run_code(python_code, "python")
        if result.success:
            print("✅ Python code executed successfully:")
            print(result.result)
        else:
            print(f"❌ Python code execution failed: {result.error_message}")
        
        # JavaScript code execution
        js_code = """
console.log("JavaScript code execution successful!");

// Get system information
const os = require('os');
const systemInfo = {
    platform: os.platform(),
    arch: os.arch(),
    nodeVersion: process.version,
    memory: Math.round(os.totalmem() / 1024 / 1024) + ' MB'
};

console.log("System info:", JSON.stringify(systemInfo, null, 2));

// Array operations
const numbers = [1, 2, 3, 4, 5];
const doubled = numbers.map(n => n * 2);
console.log("Original array:", numbers);
console.log("Doubled array:", doubled);
"""
        
        print("\n🔄 Executing JavaScript code...")
        result = session.code.run_code(js_code, "javascript")
        if result.success:
            print("✅ JavaScript code executed successfully:")
            print(result.result)
        else:
            print(f"❌ JavaScript code execution failed: {result.error_message}")
            
        # Simple file operations
        print("\n🔄 Testing file operations...")
        test_content = "Hello from AgentBay code execution!"
        write_result = session.file_system.write_file("/tmp/test_code.txt", test_content)
        if write_result.success:
            print("✅ File written successfully")
            
            read_result = session.file_system.read_file("/tmp/test_code.txt")
            if read_result.success:
                print(f"✅ File content: {read_result.content}")
            else:
                print(f"❌ File read failed: {read_result.error_message}")
        else:
            print(f"❌ File write failed: {write_result.error_message}")
            
    finally:
        # Clean up session
        print(f"\n🧹 Cleaning up code session: {session.session_id}")
        agent_bay.delete(session)

def linux_ui_automation_example(agent_bay):
    """Linux UI automation example using linux_latest image"""
    print("\n🖥️ === Linux UI Automation Example (linux_latest) ===")
    
    # Create session with linux_latest image
    print("📱 Creating session with linux_latest image...")
    params = CreateSessionParams(image_id="linux_latest")
    session_result = agent_bay.create(params)
    
    if not session_result.success:
        print(f"❌ Session creation failed: {session_result.error_message}")
        return
    
    session = session_result.session
    print(f"✅ Session created successfully: {session.session_id}")
    
    try:
        # Screenshot - Linux desktop screenshot
        print("🔄 Taking Linux desktop screenshot...")
        screenshot = session.ui.screenshot()
        if screenshot.success:
            # Save screenshot
            write_result = session.file_system.write_file("/tmp/linux_desktop_screenshot.png", screenshot.data)
            if write_result.success:
                print("✅ Linux desktop screenshot saved successfully: /tmp/linux_desktop_screenshot.png")
            else:
                print(f"❌ Screenshot save failed: {write_result.error_message}")
        else:
            print(f"❌ Screenshot failed: {screenshot.error_message}")
        
        # Test Linux-specific UI capabilities
        print("🔄 Testing Linux UI capabilities...")
        
        # Check available UI methods for Linux
        ui_methods = []
        if hasattr(session.ui, 'screenshot'):
            ui_methods.append("screenshot")
        if hasattr(session.ui, 'click'):
            ui_methods.append("click")
        if hasattr(session.ui, 'type'):
            ui_methods.append("type")
        if hasattr(session.ui, 'key'):
            ui_methods.append("key")
            
        print(f"✅ Available Linux UI methods: {', '.join(ui_methods)}")
        
        # Test basic file system operations (Linux-specific paths)
        print("\n🔄 Testing Linux file system operations...")
        linux_test_content = "Linux UI automation test file"
        linux_file_path = "/tmp/linux_ui_test.txt"
        
        write_result = session.file_system.write_file(linux_file_path, linux_test_content)
        if write_result.success:
            print(f"✅ Linux test file created: {linux_file_path}")
            
            # List files in /tmp to verify
            list_result = session.command.execute_command("ls -la /tmp/linux_ui_test.txt")
            if list_result.success:
                print(f"✅ File verified: {list_result.output.strip()}")
        else:
            print(f"❌ Linux file creation failed: {write_result.error_message}")
            
    except Exception as e:
        print(f"❌ Linux UI automation error: {e}")
        
    finally:
        # Clean up session
        print(f"\n🧹 Cleaning up Linux UI session: {session.session_id}")
        agent_bay.delete(session)

def mobile_ui_automation_example(agent_bay):
    """Mobile UI automation example using mobile_latest image"""
    print("\n📱 === Mobile UI Automation Example (mobile_latest) ===")
    
    # Create session with mobile_latest image
    print("📱 Creating session with mobile_latest image...")
    params = CreateSessionParams(image_id="mobile_latest")
    session_result = agent_bay.create(params)
    
    if not session_result.success:
        print(f"❌ Session creation failed: {session_result.error_message}")
        return
    
    session = session_result.session
    print(f"✅ Session created successfully: {session.session_id}")
    
    try:
        # Screenshot - Mobile screen screenshot
        print("🔄 Taking mobile screen screenshot...")
        screenshot = session.ui.screenshot()
        if screenshot.success:
            # Save screenshot with mobile-specific name
            write_result = session.file_system.write_file("/tmp/mobile_screen_screenshot.png", screenshot.data)
            if write_result.success:
                print("✅ Mobile screen screenshot saved successfully: /tmp/mobile_screen_screenshot.png")
            else:
                print(f"❌ Screenshot save failed: {write_result.error_message}")
        else:
            print(f"❌ Screenshot failed: {screenshot.error_message}")
        
        # Test mobile-specific UI interactions
        print("🔄 Testing mobile UI capabilities...")
        
        try:
            # Check for mobile-specific UI methods
            mobile_ui_methods = []
            if hasattr(session.ui, 'click'):
                mobile_ui_methods.append("click")
            if hasattr(session.ui, 'tap'):
                mobile_ui_methods.append("tap")  
            if hasattr(session.ui, 'swipe'):
                mobile_ui_methods.append("swipe")
            if hasattr(session.ui, 'scroll'):
                mobile_ui_methods.append("scroll")
            if hasattr(session.ui, 'type'):
                mobile_ui_methods.append("type")
                
            print(f"✅ Available mobile UI methods: {', '.join(mobile_ui_methods)}")
            
            # Try mobile touch interaction
            if hasattr(session.ui, 'click'):
                print("🔄 Testing mobile touch interaction...")
                session.ui.click(x=200, y=300)
                print("✅ Mobile touch interaction completed")
            
        except Exception as ui_error:
            print(f"⚠️ Some mobile UI features may not be available: {ui_error}")
        
        # Test mobile application management
        try:
            print("🔄 Testing mobile application management...")
            # Try to get installed apps with proper parameters for mobile
            try:
                apps = session.application.get_installed_apps(
                    start_menu=True, 
                    desktop=False, 
                    ignore_system_apps=True
                )
                if apps.success:
                    app_count = len(apps.data) if apps.data else 0
                    print(f"✅ Found {app_count} mobile applications")
                else:
                    print(f"⚠️ App listing limited: {apps.error_message}")
            except Exception as app_error:
                print(f"⚠️ Mobile app management may have limitations: {app_error}")
                
        except Exception as mobile_error:
            print(f"⚠️ Mobile-specific features may not be fully available: {mobile_error}")
        
        # Test mobile window management
        try:
            print("🔄 Testing mobile window management...")
            # Mobile environments may have different window concepts
            if hasattr(session.window, 'list_windows'):
                windows = session.window.list_windows()
                if windows.success:
                    window_count = len(windows.data) if windows.data else 0
                    print(f"✅ Found {window_count} mobile windows/activities")
                else:
                    print(f"⚠️ Window listing: {windows.error_message}")
            else:
                print("⚠️ Mobile window management uses different methods")
                
        except Exception as window_error:
            print(f"⚠️ Mobile window management may not be available: {window_error}")
            
    except Exception as e:
        print(f"❌ Mobile UI automation error: {e}")
        
    finally:
        # Clean up session
        print(f"\n🧹 Cleaning up mobile UI session: {session.session_id}")
        agent_bay.delete(session)

if __name__ == "__main__":
    main()