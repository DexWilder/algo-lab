#!/usr/bin/env bash
# create_milestone.sh — Create annotated git tag for a milestone snapshot.
#
# Usage:
#   ./scripts/create_milestone.sh <tag-name> [description]
#
# Examples:
#   ./scripts/create_milestone.sh "v0.15-phase15-gold-snapback-parent" "BB Equilibrium promoted to 6th parent"
#   ./scripts/create_milestone.sh "v0.16-phase16-strategy-controller"
#
# The script will:
#   1. Verify clean working tree (aborts if dirty)
#   2. Create an annotated git tag
#   3. Push the tag to origin
#   4. Print a zip command for optional local backup

set -euo pipefail

TAG="${1:-}"
DESC="${2:-Milestone snapshot}"

if [ -z "$TAG" ]; then
    echo "Usage: $0 <tag-name> [description]"
    echo ""
    echo "Tag format: v<major>.<minor>-phase<N>-<short-name>"
    echo "Example:    v0.15-phase15-gold-snapback-parent"
    exit 1
fi

# 1. Verify clean working tree
if [ -n "$(git status --porcelain)" ]; then
    echo "ERROR: Working tree is dirty. Commit or stash changes first."
    echo ""
    git status --short
    exit 1
fi

# Check if tag already exists
if git rev-parse "$TAG" >/dev/null 2>&1; then
    echo "ERROR: Tag '$TAG' already exists."
    echo "Use 'git tag -l' to see existing tags."
    exit 1
fi

# 2. Create annotated tag
echo "Creating tag: $TAG"
echo "Description: $DESC"
echo ""
git tag -a "$TAG" -m "$DESC"

# 3. Push tag to origin
echo "Pushing tag to origin..."
git push origin "$TAG"

# 4. Print results
echo ""
echo "=== Milestone created ==="
echo "Tag:    $TAG"
echo "Commit: $(git rev-parse --short HEAD)"
echo "Date:   $(date '+%Y-%m-%d %H:%M')"
echo ""

# Print optional zip command
REPO_NAME=$(basename "$(git rev-parse --show-toplevel)")
ZIP_NAME="${REPO_NAME}-${TAG}.zip"
echo "Optional: create a cold backup with:"
echo "  cd $(git rev-parse --show-toplevel)"
echo "  zip -r ~/$ZIP_NAME . -x '.git/*' -x 'data/*' -x '__pycache__/*' -x '*.pyc'"
