#!/bin/bash

# check-commit-version.sh - Validate current commit message includes version

set -e

VERSION_FILE="VERSION"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Read canonical version
if [[ ! -f "$VERSION_FILE" ]]; then
    echo -e "${RED}❌ VERSION file not found${NC}"
    exit 1
fi

CANONICAL_VERSION=$(cat "$VERSION_FILE" | tr -d '\n')

# Get current commit message (if available)
if git rev-parse HEAD >/dev/null 2>&1; then
    COMMIT_MSG=$(git log -1 --pretty=%B | head -n1)
    echo "📝 Current commit: $COMMIT_MSG"
    
    # Check if commit message contains version
    if [[ "$COMMIT_MSG" =~ v$CANONICAL_VERSION ]]; then
        echo -e "${GREEN}✅ Commit message contains version: v$CANONICAL_VERSION${NC}"
    else
        echo -e "${RED}❌ Commit message missing version: v$CANONICAL_VERSION${NC}"
        echo ""
        echo "Required format:"
        echo "  <type>: v$CANONICAL_VERSION - <description>"
        echo ""
        echo "Examples:"
        echo "  feat: v$CANONICAL_VERSION - add new feature"
        echo "  fix: v$CANONICAL_VERSION - resolve bug"
        echo "  release: v$CANONICAL_VERSION - complete feature X"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠️  No commit found (this is okay for initial repo)${NC}"
fi