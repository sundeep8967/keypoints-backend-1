#!/bin/bash
# Script to run shellcheck on all shell scripts
# Used for code quality validation

set -e

echo "🔍 Running shellcheck on shell scripts..."

# Find all shell scripts
SHELL_SCRIPTS=$(find scripts/ -name "*.sh" -type f)

if [ -z "$SHELL_SCRIPTS" ]; then
    echo "No shell scripts found to check"
    exit 0
fi

# Check if shellcheck is available
if ! command -v shellcheck >/dev/null 2>&1; then
    echo "⚠️ shellcheck not available, installing..."
    if command -v apt-get >/dev/null 2>&1; then
        sudo apt-get update && sudo apt-get install -y shellcheck
    elif command -v brew >/dev/null 2>&1; then
        brew install shellcheck
    else
        echo "❌ Cannot install shellcheck automatically"
        exit 1
    fi
fi

# Run shellcheck on each script with external sources
ERRORS=0
for script in $SHELL_SCRIPTS; do
    echo "Checking $script..."
    # Use -x flag to follow external sources and disable SC1091 for sourced files
    if shellcheck -x -e SC1091 "$script"; then
        echo "✅ $script passed"
    else
        echo "❌ $script failed"
        ERRORS=$((ERRORS + 1))
    fi
done

if [ $ERRORS -eq 0 ]; then
    echo "✅ All shell scripts passed shellcheck"
else
    echo "❌ $ERRORS shell scripts failed shellcheck"
    exit 1
fi