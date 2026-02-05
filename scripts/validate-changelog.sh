#!/bin/bash

# validate-changelog.sh - Ensure CHANGELOG.md has entry for current version

set -e

VERSION_FILE="VERSION"
CHANGELOG_FILE="docs/CHANGELOG.md"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Read canonical version
if [[ ! -f "$VERSION_FILE" ]]; then
    echo -e "${RED}❌ VERSION file not found${NC}"
    exit 1
fi

CANONICAL_VERSION=$(cat "$VERSION_FILE" | tr -d '\n')

# Skip check for build versions
if [[ "$CANONICAL_VERSION" =~ \+build ]]; then
    echo "🔨 Build version detected: $CANONICAL_VERSION"
    echo "✅ Skipping CHANGELOG validation for build versions"
    exit 0
fi

echo "📝 Validating CHANGELOG.md for version: $CANONICAL_VERSION"

if [[ ! -f "$CHANGELOG_FILE" ]]; then
    echo -e "${RED}❌ CHANGELOG.md not found${NC}"
    exit 1
fi

# Check if version exists in changelog
if grep -q "## \[$CANONICAL_VERSION\]" "$CHANGELOG_FILE"; then
    echo -e "${GREEN}✅ CHANGELOG.md has entry for $CANONICAL_VERSION${NC}"
    
    # Show the entry
    echo ""
    echo "📖 Changelog entry:"
    sed -n "/## \[$CANONICAL_VERSION\]/,/^## \[/p" "$CHANGELOG_FILE" | sed '$d'
else
    echo -e "${RED}❌ CHANGELOG.md missing entry for $CANONICAL_VERSION${NC}"
    echo ""
    echo "Add the following section to $CHANGELOG_FILE:"
    echo ""
    echo "## [$CANONICAL_VERSION] - $(date +%Y-%m-%d)"
    echo ""
    echo "### Added"
    echo "- New feature descriptions"
    echo ""
    echo "### Changed" 
    echo "- Modified functionality"
    echo ""
    echo "### Fixed"
    echo "- Bug fixes and patches"
    echo ""
    exit 1
fi