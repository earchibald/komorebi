#!/bin/bash

# check-version.sh - Validate version consistency across all files

set -e

VERSION_FILE="VERSION"
PYPROJECT_FILE="pyproject.toml"
PACKAGE_FILE="frontend/package.json"
CHANGELOG_FILE="docs/CHANGELOG.md"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🔍 Checking version consistency..."
echo ""

# Read canonical version
if [[ ! -f "$VERSION_FILE" ]]; then
    echo -e "${RED}❌ VERSION file not found${NC}"
    exit 1
fi

CANONICAL_VERSION=$(cat "$VERSION_FILE" | tr -d '\n')
echo "📄 Canonical version: $CANONICAL_VERSION"

# Validate version format
if [[ ! "$CANONICAL_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+(\+build[0-9]+)?$ ]]; then
    echo -e "${RED}❌ Invalid version format: $CANONICAL_VERSION${NC}"
    echo "   Expected: MAJOR.MINOR.PATCH[+buildN]"
    exit 1
fi

# Check pyproject.toml
if [[ ! -f "$PYPROJECT_FILE" ]]; then
    echo -e "${RED}❌ pyproject.toml not found${NC}"
    exit 1
fi

PYPROJECT_VERSION=$(grep '^version = ' "$PYPROJECT_FILE" | sed 's/version = "\(.*\)"/\1/')
echo "🐍 pyproject.toml version: $PYPROJECT_VERSION"

if [[ "$PYPROJECT_VERSION" != "$CANONICAL_VERSION" ]]; then
    echo -e "${RED}❌ pyproject.toml version mismatch${NC}"
    echo "   Expected: $CANONICAL_VERSION"
    echo "   Found: $PYPROJECT_VERSION"
    echo "   Run: ./scripts/sync-versions.sh"
    exit 1
fi

# Check package.json
if [[ ! -f "$PACKAGE_FILE" ]]; then
    echo -e "${RED}❌ frontend/package.json not found${NC}"
    exit 1
fi

PACKAGE_VERSION=$(grep '"version":' "$PACKAGE_FILE" | sed 's/.*"version": "\(.*\)".*/\1/')
echo "⚛️  package.json version: $PACKAGE_VERSION"

if [[ "$PACKAGE_VERSION" != "$CANONICAL_VERSION" ]]; then
    echo -e "${RED}❌ package.json version mismatch${NC}"
    echo "   Expected: $CANONICAL_VERSION"
    echo "   Found: $PACKAGE_VERSION"
    echo "   Run: ./scripts/sync-versions.sh"
    exit 1
fi

# Check changelog (only for release versions, not +buildN)
if [[ ! "$CANONICAL_VERSION" =~ \+build ]]; then
    if [[ ! -f "$CHANGELOG_FILE" ]]; then
        echo -e "${RED}❌ CHANGELOG.md not found${NC}"
        exit 1
    fi
    
    if ! grep -q "## \[$CANONICAL_VERSION\]" "$CHANGELOG_FILE"; then
        echo -e "${YELLOW}⚠️  CHANGELOG.md missing entry for $CANONICAL_VERSION${NC}"
        echo "   Add entry before release"
        exit 1
    fi
    echo "📝 CHANGELOG.md has entry for $CANONICAL_VERSION"
else
    echo "🔨 Build version - skipping CHANGELOG check"
fi

echo ""
echo -e "${GREEN}✅ All versions consistent: $CANONICAL_VERSION${NC}"