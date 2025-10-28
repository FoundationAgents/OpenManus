#!/bin/bash

echo "Installing Git hooks..."
cp hooks/pre-commit .git/hooks/
chmod +x .git/hooks/pre-commit
echo "✅ Git hooks installed."
