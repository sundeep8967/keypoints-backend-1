#!/bin/bash
# Script to set up Playwright browsers with caching
# Used by GitHub Actions workflow
# shellcheck source=scripts/error_handler.sh

# Source error handler
source "$(dirname "$0")/error_handler.sh"

log_info "Setting up Playwright browsers..."

# Set Playwright environment variable
export PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH:-$HOME/pw-browsers}"

# Check if browsers are already cached
if [ -d "$PLAYWRIGHT_BROWSERS_PATH" ] && [ "$(ls -A "$PLAYWRIGHT_BROWSERS_PATH" 2>/dev/null)" ]; then
    log_success "Using cached Playwright browsers from $PLAYWRIGHT_BROWSERS_PATH"
    exit 0
fi

log_info "📥 Installing Playwright browsers (will be cached for next run)"

# Create browsers directory
mkdir -p "$PLAYWRIGHT_BROWSERS_PATH"

# Install Playwright browsers with retry
if retry_command 3 10 playwright install chromium --with-deps; then
    log_success "Playwright browsers installed successfully"
else
    log_warn "Playwright installation failed, will fallback to Selenium"
    exit 0  # Don't fail the workflow, just continue without Playwright
fi