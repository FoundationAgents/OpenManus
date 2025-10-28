#!/bin/bash
set -euo pipefail

# Sync current (or specified) branch: pull from aliyun-agentbay, push to inner and origin
# Usage:
#   ./sync-aliyun-to-remotes.sh                # use current branch
#   ./sync-aliyun-to-remotes.sh <branch>       # specify branch name
#   REMOTES can be overridden: REMOTES="inner origin" ./sync-aliyun-to-remotes.sh

REMOTE_SOURCE=${REMOTE_SOURCE:-aliyun-agentbay}
REMOTES=${REMOTES:-"inner origin"}
BRANCH=${1:-$(git branch --show-current)}

if [[ -z "$BRANCH" ]]; then
  echo "Error: could not determine current branch. Please specify explicitly." >&2
  exit 1
fi

# Verify remotes exist
if ! git remote get-url "$REMOTE_SOURCE" >/dev/null 2>&1; then
  echo "Error: source remote '$REMOTE_SOURCE' does not exist." >&2
  exit 1
fi
for r in $REMOTES; do
  if ! git remote get-url "$r" >/dev/null 2>&1; then
    echo "Error: target remote '$r' does not exist." >&2
    exit 1
  fi
done

# Fetch latest from all remotes
git fetch "$REMOTE_SOURCE" --prune
for r in $REMOTES; do
  git fetch "$r" --prune || true
done

# Ensure local branch exists and checkout
if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
  git checkout "$BRANCH"
else
  # Create local branch tracking source remote branch if exists
  if git ls-remote --exit-code --heads "$REMOTE_SOURCE" "$BRANCH" >/dev/null 2>&1; then
    git checkout -b "$BRANCH" --track "$REMOTE_SOURCE/$BRANCH"
  else
    echo "Error: branch '$BRANCH' not found on $REMOTE_SOURCE." >&2
    exit 1
  fi
fi

# Reset local branch to source remote branch state
# Use hard reset to guarantee exact mirror
SRC_REF="$REMOTE_SOURCE/$BRANCH"
echo "Syncing local '$BRANCH' to '$SRC_REF'..."
git reset --hard "$SRC_REF"

# Push to each target remote with protection against overwriting unexpected changes
for r in $REMOTES; do
  echo "Pushing '$BRANCH' to '$r'..."
  git push "$r" "$BRANCH" --force-with-lease
done

echo "Done. Branch '$BRANCH' synced from '$REMOTE_SOURCE' to: $REMOTES"