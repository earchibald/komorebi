#!/bin/bash

# sync-versions.sh - Update all version files to match VERSION

set -e

VERSION_FILE="VERSION"
PYPROJECT_FILE="pyproject.toml"
PACKAGE_FILE="frontend/package.json"

# Colors for output
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Read canonical version
if [[ ! -f "$VERSION_FILE" ]]; then
    echo "❌ VERSION file not found"
    exit 1
fi

CANONICAL_VERSION=$(cat "$VERSION_FILE" | tr -d '\n')
echo "🔄 Syncing all files to version: $CANONICAL_VERSION"

# Update pyproject.toml
if [[ -f "$PYPROJECT_FILE" ]]; then
    sed -i '' "s/^version = .*/version = \"$CANONICAL_VERSION\"/" "$PYPROJECT_FILE"
    echo "✅ Updated pyproject.toml"
else
    echo "⚠️  pyproject.toml not found"
fi

# Update package.json
if [[ -f "$PACKAGE_FILE" ]]; then
    sed -i '' "s/\"version\": \"[^\"]*\"/\"version\": \"$CANONICAL_VERSION\"/" "$PACKAGE_FILE"
    echo "✅ Updated package.json"
else
    echo "⚠️  package.json not found"
fi

echo ""
echo -e "${GREEN}✅ All versions synced to: $CANONICAL_VERSION${NC}"
echo ""
echo "Next steps:"
echo "  git add VERSION pyproject.toml frontend/package.json"
echo "  git commit -m \"chore: v$CANONICAL_VERSION - sync versions\""