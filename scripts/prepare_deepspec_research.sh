#!/usr/bin/env bash
set -euo pipefail

# Helper script to prepare DeepSpec research repository
# This clones or updates DeepSpec into research/deepspec/upstream.
# It does NOT run training automatically.

CHECKOUT_DIR="research/deepspec/upstream"
REPO_URL="https://github.com/deepseek-ai/DeepSpec.git"

echo "=== DeepSpec Research Preparation ==="
echo "Note: DeepSpec requires substantial GPU/storage resources (target caches can be ~38TB)."
echo "This script only clones or updates the upstream code for future research/evaluation."

mkdir -p "$(dirname "$CHECKOUT_DIR")"

if [ -d "$CHECKOUT_DIR/.git" ]; then
    echo "Updating existing DeepSpec repository in $CHECKOUT_DIR..."
    git -C "$CHECKOUT_DIR" pull --ff-only || {
        echo "Warning: git pull failed, keeping current checkout."
    }
else
    echo "Cloning DeepSpec into $CHECKOUT_DIR..."
    git clone "$REPO_URL" "$CHECKOUT_DIR"
fi

echo "DeepSpec repository ready in $CHECKOUT_DIR."
echo "See research/deepspec/README.md for usage and evaluation workflows."
