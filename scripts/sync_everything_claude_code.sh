#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="${TMPDIR:-/tmp}/everything-claude-code-sync"
SRC_REPO="${1:-https://github.com/affaan-m/everything-claude-code.git}"

rm -rf "$TMP_DIR"
git clone --depth=1 "$SRC_REPO" "$TMP_DIR"

mkdir -p "$ROOT_DIR/vendor/everything-claude-code"
rsync -a --delete "$TMP_DIR/skills/" "$ROOT_DIR/vendor/everything-claude-code/skills/"
rsync -a --delete "$TMP_DIR/agents/" "$ROOT_DIR/vendor/everything-claude-code/agents/"
rsync -a --delete "$TMP_DIR/.agents/skills/" "$ROOT_DIR/vendor/everything-claude-code/agents-skills/"

echo "Synced skills + agents into vendor/everything-claude-code"
