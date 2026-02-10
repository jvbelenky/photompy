#!/usr/bin/env bash
set -euo pipefail

VERSION_FILE="src/photompy/_version.py"
CHANGELOG="CHANGELOG.md"

die() { echo "Error: $*" >&2; exit 1; }

# --- Read current version ---
current=$(grep -oP '(?<=__version__ = ")[^"]+' "$VERSION_FILE")
IFS='.' read -r major minor patch <<< "$current"

# --- Determine new version ---
case "${1:-}" in
    major) new_version="$((major + 1)).0.0" ;;
    minor) new_version="$major.$((minor + 1)).0" ;;
    patch) new_version="$major.$minor.$((patch + 1))" ;;
    [0-9]*) new_version="$1" ;;
    *)
        echo "Usage: $0 <major|minor|patch|X.Y.Z>"
        echo ""
        echo "Current version: $current"
        echo ""
        echo "Examples:"
        echo "  $0 patch   # $current -> $major.$minor.$((patch + 1))"
        echo "  $0 minor   # $current -> $major.$((minor + 1)).0"
        echo "  $0 major   # $current -> $((major + 1)).0.0"
        echo "  $0 1.0.0   # $current -> 1.0.0"
        exit 1
        ;;
esac

echo "Releasing: $current -> $new_version"

# --- Preflight checks ---
git diff --quiet && git diff --cached --quiet \
    || die "Working tree is dirty. Commit or stash changes first."

branch=$(git rev-parse --abbrev-ref HEAD)
[ "$branch" = "main" ] || die "Must be on main branch (currently on $branch)"

grep -q "## \[Unreleased\]" "$CHANGELOG" \
    || die "CHANGELOG.md missing [Unreleased] section"

# Check that Unreleased section has content
unreleased_content=$(sed -n '/## \[Unreleased\]/,/## \[/{/## \[/d; /^$/d; p;}' "$CHANGELOG")
[ -n "$unreleased_content" ] \
    || die "No content in [Unreleased] section. Add changelog entries first."

# --- Update version file ---
sed -i "s/__version__ = \".*\"/__version__ = \"$new_version\"/" "$VERSION_FILE"

# --- Update changelog ---
today=$(date +%Y-%m-%d)
sed -i "s/## \[Unreleased\]/## [Unreleased]\n\n## [$new_version] - $today/" "$CHANGELOG"

# --- Commit, tag, push ---
git add "$VERSION_FILE" "$CHANGELOG"
git commit -m "Release v$new_version"
git tag -a "v$new_version" -m "Release v$new_version"
git push origin main
git push origin "v$new_version"

echo ""
echo "Released v$new_version"
echo "Tagged and pushed v$new_version. Now uploading to PyPI and creating GitHub release..."
