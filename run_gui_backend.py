import os
import subprocess
import sys

def get_project_root():
    # Assumes run_gui_backend.py is in the project root
    return os.path.dirname(os.path.abspath(__file__))

if __name__ == "__main__":
    project_root = get_project_root()
    
    # Uvicorn needs to be run where it can find `gui.backend.main:app`.
    # Running from project_root and Python's default module resolution
    # should handle this if `gui` is a package (has __init__.py, though not strictly necessary for namespace packages).
    # The sys.path modification in app/logger.py should ensure it can find gui.backend too.

    command = [
        sys.executable, # Use the current Python interpreter
        "-m", "uvicorn",
        "gui.backend.main:app",
        "--host", "0.0.0.0",
        "--port", "8008",
        "--reload" # For development convenience
    ]
    
    print(f"Starting GUI backend server...")
    print(f"Project root (running from): {project_root}")
    print(f"Command: {' '.join(command)}")
    
    process = None # Initialize process to None
    try:
        # Execute Uvicorn, setting cwd to project_root ensures consistent import behavior
        process = subprocess.Popen(command, cwd=project_root)
        process.wait()
    except KeyboardInterrupt:
        print("GUI Backend server shutdown requested.")
        if process: # Ensure process exists before trying to terminate
            process.terminate()
            process.wait()
    except Exception as e:
        print(f"Failed to start GUI backend server: {e}")
