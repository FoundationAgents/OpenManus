#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Change to the script's directory
cd "$SCRIPT_DIR" || exit

# Run the launcher script
echo "Starting OpenManus..."
python3 openmanus_launcher.py

# Check for errors
if [ $? -ne 0 ]; then
    echo ""
    echo "OpenManus launcher exited with an error."
    # No direct 'pause' equivalent that works universally without user interaction.
    # The error message will remain visible in the terminal.
fi
