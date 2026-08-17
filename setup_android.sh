#!/bin/bash

# OpenManus Android (Termux + PRoot) Automated Installer
# This script automates setting up the full Linux environment, compile stack, 
# Chromium, Node.js, and Python dependencies required to run OpenManus on Android.

set -e

echo "=========================================================="
echo "      OpenManus Android Installer & Environment Setup     "
echo "=========================================================="

# Helper function to prompt user
prompt_yes_no() {
    local prompt_msg="$1"
    local default_val="$2"
    local user_input
    
    if [ "$default_val" = "Y" ]; then
        prompt_msg="$prompt_msg [Y/n]: "
    else
        prompt_msg="$prompt_msg [y/N]: "
    fi
    
    read -p "$prompt_msg" user_input
    user_input=$(echo "$user_input" | tr '[:upper:]' '[:lower:]')
    
    if [ -z "$user_input" ]; then
        if [ "$default_val" = "Y" ]; then
            return 0
        else
            return 1
        fi
    fi
    
    if [ "$user_input" = "y" ] || [ "$user_input" = "yes" ]; then
        return 0
    else
        return 1
    fi
}

# 1. Detect if we are inside Termux (Host Android)
# PROOT_DISTRO_DEV is set when this script re-invokes itself inside PRoot to prevent infinite recursion
if [ -d "/data/data/com.termux" ] && [ -z "$PROOT_DISTRO_DEV" ]; then
    echo "Status: Running inside Termux (Host Android environment)"
    
    # Ensure proot-distro is installed
    if ! command -v proot-distro >/dev/null 2>&1; then
        echo "PRoot Distro is required to run a standard Linux environment inside Termux."
        if prompt_yes_no "Would you like to install proot-distro automatically?" "Y"; then
            echo "Installing proot-distro..."
            pkg update -y
            pkg install proot-distro -y
        else
            echo "Error: PRoot Distro is required. Exiting."
            exit 1
        fi
    fi
    
    # Check for installed distributions
    echo "Checking for Ubuntu distribution inside PRoot..."
    if ! proot-distro list | grep -A 5 "ubuntu" | grep -q "Installed: yes"; then
        echo "Ubuntu is not installed inside PRoot. Ubuntu is recommended for full compatibility."
        if prompt_yes_no "Would you like to install Ubuntu inside PRoot now?" "Y"; then
            echo "Installing Ubuntu inside PRoot (this may take a few minutes)..."
            proot-distro install ubuntu
        else
            echo "Error: Ubuntu inside PRoot is required. Exiting."
            exit 1
        fi
    fi
    
    # Set up launcher and invoke setup inside Ubuntu
    echo "Ubuntu inside PRoot is ready."
    REPO_PATH=$(pwd)
    echo "Sharing and executing setup inside PRoot Ubuntu..."
    
    # We copy the script and run it inside PRoot
    export PROOT_DISTRO_DEV=1
    SCRIPT_NAME=$(basename "${BASH_SOURCE[0]}")
    proot-distro login ubuntu --shared-tmp -- bash -c "cd \"$REPO_PATH\" && bash \"$SCRIPT_NAME\"" || {
        echo "Error: Installation inside PRoot Ubuntu failed."
        exit 1
    }
    
    echo "=========================================================="
    echo "Setup finished! You can now start OpenManus with:"
    echo "  proot-distro login ubuntu --shared-tmp -- bash -c \"cd \\\"$REPO_PATH\\\" && ./run_android.sh\""
    echo "=========================================================="
    exit 0
fi

# 2. PRoot environment setup (Ubuntu/Debian environment)
echo "Status: Setting up environment dependencies inside PRoot distro"

# Ensure we are running as root or have sudo (PRoot runs as root by default)
APT_CMD="apt-get"
if command -v apt &> /dev/null; then
    APT_CMD="apt"
fi

echo "Updating system packages..."
$APT_CMD update -y

echo "Installing core dependencies, compiler stack, Python and Git..."
$APT_CMD install -y \
    build-essential \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    git \
    curl \
    rustc \
    cargo \
    libffi-dev \
    libssl-dev

echo "Installing Chromium (for Browser tool)..."
$APT_CMD install -y chromium-browser || $APT_CMD install -y chromium

echo "Installing Node.js and NPM (for Chart Visualization)..."
$APT_CMD install -y nodejs npm

# Create/Verify Workspace Directory and Config File
mkdir -p workspace/sandbox
if [ ! -f "config/config.toml" ] && [ -f "config/config.example.toml" ]; then
    echo "Creating config/config.toml from example..."
    cp config/config.example.toml config/config.toml
fi

# 3. Create Python Virtual Environment
echo "Setting up Python Virtual Environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

echo "Upgrading pip, setuptools and wheel..."
pip install --upgrade pip setuptools wheel

echo "Installing Python dependencies from requirements.txt (this may take some time as some native wheels compile)..."
pip install -r requirements.txt

# 4. Generate the run script
echo "Creating runner script (run_android.sh)..."
cat << 'EOF' > run_android.sh
#!/bin/bash
# OpenManus runner script for Android
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/venv/bin/activate"
python3 "$SCRIPT_DIR/main.py" "$@"
EOF
chmod +x run_android.sh

echo "=========================================================="
echo "          OpenManus Android Setup Completed!              "
echo "=========================================================="
echo "You can now run OpenManus using:"
echo "  ./run_android.sh"
echo "=========================================================="
