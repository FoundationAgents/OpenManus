"""
Minimal configuration test that doesn't depend on pydantic.
"""

import os
from pathlib import Path

# Simple configuration without pydantic
class SimpleConfig:
    def __init__(self):
        self.workspace_root = Path("./workspace").resolve()
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        
        # Local service settings
        self.local_service = SimpleLocalServiceConfig()
        
        # UI settings
        self.ui = SimpleUIConfig()

class SimpleLocalServiceConfig:
    def __init__(self):
        self.workspace_directory = "./workspace"
        self.python_executable = "python3"
        self.max_concurrent_processes = 5
        self.process_timeout = 300
        self.enable_network = True
        self.allowed_commands = ["python", "pip", "git", "npm", "node", "bash", "cmd", "powershell"]

class SimpleUIConfig:
    def __init__(self):
        self.enable_gui = True
        self.enable_webui = True
        self.webui_port = 8080
        self.webui_host = "localhost"
        self.theme = "dark"
        self.window_width = 1200
        self.window_height = 800
        self.auto_save = True

# Test simple config
def test_simple_config():
    print("Testing simple configuration...")
    
    config = SimpleConfig()
    print(f"✓ Workspace: {config.workspace_root}")
    print(f"✓ Local service workspace: {config.local_service.workspace_directory}")
    print(f"✓ UI GUI enabled: {config.ui.enable_gui}")
    print(f"✓ UI WebUI enabled: {config.ui.enable_webui}")
    
    # Test workspace operations
    test_file = config.workspace_root / "test.txt"
    test_file.write_text("Simple config test")
    content = test_file.read_text()
    
    if content == "Simple config test":
        print("✓ File operations work")
        test_file.unlink()
        return True
    else:
        print("✗ File operations failed")
        return False

if __name__ == "__main__":
    if test_simple_config():
        print("✓ Simple configuration test passed!")
    else:
        print("✗ Simple configuration test failed!")