#!/bin/bash

# Sync from GitHub (upstream) to Internal GitLab (origin)
# This script handles the squash-merge issue by force-syncing from upstream

set -e

echo "🔄 Starting sync from GitHub to Internal GitLab..."

# Fetch all remotes
echo "📥 Fetching from all remotes..."
git fetch origin
git fetch upstream

# Get current branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "📍 Current branch: $CURRENT_BRANCH"

# Switch to main if not already there
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo "🔀 Switching to main branch..."
    git checkout main
fi

# Check if there are uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo "❌ Error: You have uncommitted changes. Please commit or stash them first."
    exit 1
fi

# Check if local main has commits not in upstream
LOCAL_COMMITS=$(git rev-list upstream/main..main --count)
if [ "$LOCAL_COMMITS" -gt 0 ]; then
    echo "⚠️  Warning: Your local main has $LOCAL_COMMITS commit(s) not in upstream/main"
    echo "These commits will be lost if you continue. They might be:"
    git log upstream/main..main --oneline
    echo ""
    read -p "Do you want to continue? This will reset your local main to match upstream/main. (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Sync cancelled."
        exit 1
    fi
fi

# Reset local main to upstream/main
echo "🔄 Resetting local main to match upstream/main..."
git reset --hard upstream/main

# Force push to origin (internal GitLab)
echo "📤 Force pushing to internal GitLab (origin)..."
git push origin main --force-with-lease

echo "✅ Sync completed successfully!"
echo "📊 Current status:"
git log --oneline -5

