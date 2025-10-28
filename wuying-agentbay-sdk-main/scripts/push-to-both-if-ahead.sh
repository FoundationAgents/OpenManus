#!/bin/bash
set -euo pipefail

# Push current (or specified) branch to origin and inner only if there are new local commits.
# Usage:
#   ./push-to-both-if-ahead.sh            # use current branch
#   ./push-to-both-if-ahead.sh <branch>   # specify branch
#   REMOTES can be overridden: REMOTES="origin inner" ./push-to-both-if-ahead.sh

REMOTES=${REMOTES:-"origin inner"}
BRANCH=${1:-$(git branch --show-current)}

if [[ -z "$BRANCH" ]]; then
  echo "Error: could not determine current branch. Please specify explicitly." >&2
  exit 1
fi

# Verify remotes exist
for r in $REMOTES; do
  if ! git remote get-url "$r" >/dev/null 2>&1; then
    echo "Error: remote '$r' does not exist." >&2
    exit 1
  fi
done

# Ensure we are on the branch to check/push
if [[ $(git branch --show-current) != "$BRANCH" ]]; then
  git checkout "$BRANCH"
fi

# Fetch references to compare
for r in $REMOTES; do
  git fetch "$r" --prune >/dev/null 2>&1 || true
  # Determine ahead count
  if git rev-parse --verify -q "refs/remotes/$r/$BRANCH" >/dev/null; then
    AHEAD=$(git rev-list --left-right --count "$r/$BRANCH"..."$BRANCH" | awk '{print $2}')
  else
    # Remote branch missing: treat as ahead if local exists
    AHEAD=$(git rev-list --count "$BRANCH")
  fi
  if [[ "$AHEAD" -gt 0 ]]; then
    echo "Local branch '$BRANCH' is ahead of '$r/$BRANCH' by $AHEAD commit(s). Pushing..."
    git push "$r" "$BRANCH"
  else
    echo "No new commits to push for '$BRANCH' to remote '$r'."
  fi
done

echo "Done."