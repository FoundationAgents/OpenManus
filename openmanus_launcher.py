import sys
import subprocess
import os
import shutil
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib # type: ignore

# Constants adapted from setup_env.py
MIN_PYTHON_VERSION = (3, 12)
VENV_NAME = ".venv"
REQUIREMENTS_FILE = "requirements.txt"
CONFIG_DIR = "config"
CONFIG_FILE_NAME = "config.toml"
DEFAULT_CONFIG_FILE_NAME = "config.example.toml"
WORKSPACE_DIR = "workspace"

# API Key provided in the prompt
USER_PROVIDED_API_KEY = "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"

def check_python_version():
    """Checks if the current Python version meets the minimum requirement."""
    print("Checking Python version...")
    if sys.version_info < MIN_PYTHON_VERSION:
        print(
            f"Error: Python {MIN_PYTHON_VERSION[0]}.{MIN_PYTHON_VERSION[1]} or higher is required."
        )
        print(f"You are running Python {sys.version_info[0]}.{sys.version_info[1]}.")
        sys.exit(1)
    print(f"Python version {sys.version_info[0]}.{sys.version_info[1]} is sufficient.")

def get_venv_python_executable():
    """Returns the path to the Python executable within the virtual environment."""
    # Path depends on OS.
    if os.name == "nt":  # Windows
        return os.path.join(VENV_NAME, "Scripts", "python.exe")
    else:  # macOS/Linux
        return os.path.join(VENV_NAME, "bin", "python")

def create_virtual_environment():
    """
    Creates a virtual environment if it doesn't already exist.
    Returns True if newly created, False if it already existed.
    """
    print("Checking for virtual environment...")
    venv_python = get_venv_python_executable()
    if os.path.exists(venv_python) and os.path.exists(VENV_NAME):
        print(f"Virtual environment '{VENV_NAME}' already exists.")
        return False
    else:
        print(f"Creating virtual environment '{VENV_NAME}'...")
        try:
            subprocess.run([sys.executable, "-m", "venv", VENV_NAME], check=True)
            print("Virtual environment created successfully.")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error creating virtual environment: {e}")
            sys.exit(1)

def install_dependencies(venv_python_executable):
    """Installs dependencies from requirements.txt into the virtual environment."""
    print("Installing dependencies...")
    if not os.path.exists(REQUIREMENTS_FILE):
        print(f"Error: {REQUIREMENTS_FILE} not found.")
        sys.exit(1)
    try:
        subprocess.run(
            [venv_python_executable, "-m", "pip", "install", "-r", REQUIREMENTS_FILE],
            check=True,
            capture_output=True,
            text=True
        )
        print("Dependencies installed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error installing dependencies: {e}")
        print("stdout:", e.stdout)
        print("stderr:", e.stderr)
        sys.exit(1)

def ensure_playwright_installed(venv_python_executable):
    """Ensures Playwright browsers are installed in the virtual environment."""
    print("Checking and installing Playwright browsers if necessary...")
    try:
        subprocess.run(
            [venv_python_executable, "-m", "playwright", "install"],
            check=True,
            capture_output=True,
            text=True
        )
        print("Playwright browsers are installed/updated.")
    except subprocess.CalledProcessError as e:
        print(f"Error installing Playwright browsers: {e}")
        print("stdout:", e.stdout)
        print("stderr:", e.stderr)
        # Depending on the error, we might not want to exit.
        # For example, if it's just a warning or if browsers are already installed.
        # However, the prompt asked for check=True, implying we should exit on error.
        sys.exit(1)

def ensure_config_file_and_api_key(api_key_value=None):
    """
    Ensures the config file exists, is copied from example if not,
    and that the API key is set.
    """
    print("Ensuring configuration file and API key...")
    os.makedirs(CONFIG_DIR, exist_ok=True)
    config_path = os.path.join(CONFIG_DIR, CONFIG_FILE_NAME)
    example_config_path = os.path.join(CONFIG_DIR, DEFAULT_CONFIG_FILE_NAME)

    if not os.path.exists(example_config_path):
        print(f"Error: Default configuration file '{example_config_path}' not found. Cannot proceed.")
        sys.exit(1)

    if not os.path.exists(config_path):
        print(f"Configuration file '{config_path}' not found. Copying from '{example_config_path}'...")
        try:
            shutil.copy(example_config_path, config_path)
            print(f"Copied '{example_config_path}' to '{config_path}'.")
        except IOError as e:
            print(f"Error copying configuration file: {e}")
            sys.exit(1)

    # Read and update API key
    try:
        with open(config_path, "rb") as f:
            config_data = tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        print(f"Error decoding TOML from '{config_path}': {e}")
        sys.exit(1)
    except IOError as e:
        print(f"Error reading configuration file '{config_path}': {e}")
        sys.exit(1)

    api_key_present = False
    if "llm" in config_data and "api_key" in config_data["llm"]:
        current_api_key = config_data["llm"]["api_key"]
        if current_api_key and current_api_key != "YOUR_API_KEY" and "PLACEHOLDER" not in current_api_key.upper():
            api_key_present = True
            print("API key found in configuration file.")

    if not api_key_present:
        print("API key not found or is a placeholder in the configuration file.")
        new_api_key = api_key_value
        if not new_api_key:
            new_api_key = input("Please enter your API key: ").strip()

        if not new_api_key:
            print("No API key provided. Please set it manually in 'config/config.toml'.")
            # Not exiting, as the application might have other functionalities or a default behavior.
            # However, for this specific flow, an API key is crucial.
            # For now, we will proceed, but this might need adjustment based on run_flow.py behavior.
            return

        # Update the TOML file with the new API key (text-based replacement)
        print(f"Updating API key in '{config_path}'...")
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            updated_lines = []
            in_llm_section = False
            api_key_updated_in_file = False
            for line in lines:
                if line.strip() == "[llm]":
                    in_llm_section = True
                elif line.strip().startswith("[") and line.strip() != "[llm]":
                    in_llm_section = False

                if in_llm_section and line.strip().startswith("api_key"):
                    updated_lines.append(f'api_key = "{new_api_key}"\n')
                    api_key_updated_in_file = True
                else:
                    updated_lines.append(line)

            if not api_key_updated_in_file:
                # If api_key line was not found under [llm], append it.
                # This is a fallback, ideally the example config has the key.
                print("api_key line not found under [llm] section, attempting to add it.")
                final_lines = []
                llm_section_exists = any(line.strip() == "[llm]" for line in updated_lines)
                if not llm_section_exists:
                    final_lines.append("[llm]\n")
                    final_lines.append(f'api_key = "{new_api_key}"\n')
                    final_lines.extend(updated_lines) # Add original lines after new section
                else: # llm section exists, but no api_key line.
                    for line_idx, line_content in enumerate(updated_lines):
                        final_lines.append(line_content)
                        if line_content.strip() == "[llm]":
                            # Check if next line is already api_key (e.g. if placeholder was just an empty string)
                            # This check is a bit fragile.
                            if not (line_idx + 1 < len(updated_lines) and updated_lines[line_idx+1].strip().startswith("api_key")):
                                final_lines.append(f'api_key = "{new_api_key}"\n')


                updated_lines = final_lines


            with open(config_path, "w", encoding="utf-8") as f:
                f.writelines(updated_lines)
            print("API key updated in configuration file.")

        except IOError as e:
            print(f"Error writing updated configuration file '{config_path}': {e}")
            print("Please set the API key manually.")
            # Not exiting, to allow application to proceed if possible.
    else:
        if api_key_value and config_data.get("llm", {}).get("api_key") != api_key_value:
            print("An API key exists in the config file, but a different one was provided to the launcher.")
            print("The existing key in the file will be used. To use the new key, please update config/config.toml manually or remove it to allow the launcher to set it.")


def create_workspace_directory():
    """Creates the workspace directory if it doesn't exist."""
    print(f"Ensuring workspace directory '{WORKSPACE_DIR}' exists...")
    try:
        os.makedirs(WORKSPACE_DIR, exist_ok=True)
        print(f"Workspace directory '{WORKSPACE_DIR}' is ready.")
    except OSError as e:
        print(f"Error creating workspace directory '{WORKSPACE_DIR}': {e}")
        sys.exit(1)

def launch_application(venv_python_executable):
    """Launches the main application GUI script."""
    print("Launching the application GUI (app_gui.py)...")
    gui_script = "app_gui.py" # Assuming it's in the root
    if not os.path.exists(gui_script):
        print(f"Error: Main application GUI script '{gui_script}' not found in the current directory.")
        print("Please ensure the launcher is run from the repository root.")
        sys.exit(1)
    try:
        # Using os.environ.copy() ensures the subprocess inherits the current environment
        env = os.environ.copy()
        # Activate venv for the subprocess by modifying PATH might be more robust
        # but for direct calls to venv_python_executable, it's usually fine.
        # However, app_gui.py might itself call other scripts/tools.
        # Let's ensure the venv's bin/Scripts directory is at the start of PATH
        venv_scripts_dir = os.path.dirname(venv_python_executable)
        env["PATH"] = venv_scripts_dir + os.pathsep + env.get("PATH", "")

        # Some applications might need to know they are in a venv
        env["VIRTUAL_ENV"] = os.path.abspath(VENV_NAME)


        process = subprocess.run(
            [venv_python_executable, gui_script],
            check=True,
            text=True, # Capture output as text
            env=env
        )
        # If check=True and the process exits with non-zero, CalledProcessError will be raised.
        # If we want to see output even on success, we can print process.stdout, process.stderr
        print("Application GUI launched successfully.")
        if process.stdout:
            print("Application GUI stdout:\n", process.stdout)
        if process.stderr:
            print("Application GUI stderr:\n", process.stderr) # Should be empty on success normally

    except subprocess.CalledProcessError as e:
        print(f"Application GUI '{gui_script}' exited with an error (return code {e.returncode}).")
        if e.stdout:
            print("Application GUI stdout:\n", e.stdout)
        if e.stderr:
            print("Application GUI stderr:\n", e.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print(f"Error: The Python executable '{venv_python_executable}' was not found for launching the application GUI.")
        sys.exit(1)


if __name__ == "__main__":
    print("--- OpenManus Launcher Initializing ---")

    check_python_version()
    created_new_env = create_virtual_environment()

    venv_python = get_venv_python_executable()

    # If a new venv was created, dependencies must be installed.
    # If venv existed, we could potentially skip, but re-running is safer for ensuring updates.
    install_dependencies(venv_python)

    ensure_playwright_installed(venv_python)

    ensure_config_file_and_api_key(api_key_value=USER_PROVIDED_API_KEY)

    create_workspace_directory()

    launch_application(venv_python)

    print("--- OpenManus Launcher Finished ---")
