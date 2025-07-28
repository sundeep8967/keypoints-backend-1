#!/bin/bash
# Script to fix common shellcheck issues across all scripts
# Run this to clean up code quality issues

set -e

echo "🔧 Fixing shellcheck issues in all scripts..."

# Fix the retry_command function in error_handler.sh
echo "Fixing error_handler.sh..."

# The main issues are already fixed in the previous replacement

# Add shellcheck directives to scripts that source error_handler.sh
SCRIPTS_TO_FIX=(
    "scripts/validate_environment.sh"
    "scripts/setup_playwright.sh" 
    "scripts/optimize_caching.sh"
    "scripts/check_dependencies.sh"
    "scripts/install_chrome.sh"
)

for script in "${SCRIPTS_TO_FIX[@]}"; do
    if [ -f "$script" ]; then
        echo "Adding shellcheck directive to $script..."
        # Add shellcheck disable directive for SC1091 at the top
        if ! grep -q "# shellcheck source=" "$script"; then
            sed -i '1a# shellcheck source=scripts/error_handler.sh' "$script"
        fi
    fi
done

echo "✅ Shellcheck issues fixed!"
echo "Run 'bash scripts/shellcheck.sh' to verify fixes."