#!/bin/bash
# Script to debug caching issues
# shellcheck source=scripts/error_handler.sh

# Source error handler
source "$(dirname "$0")/error_handler.sh"

log_info "🔍 Debugging cache configuration..."

# Show environment variables
log_info "Environment variables:"
log_info "  PLAYWRIGHT_BROWSERS_PATH: ${PLAYWRIGHT_BROWSERS_PATH:-'not set'}"
log_info "  PIP_CACHE_DIR: ${PIP_CACHE_DIR:-'not set'}"
log_info "  NLTK_DATA: ${NLTK_DATA:-'not set'}"

# Check cache directories
log_info "Cache directory status:"
for dir in "$PLAYWRIGHT_BROWSERS_PATH" "$PIP_CACHE_DIR" "$HOME/nltk_data" "$HOME/.cache/selenium" "$HOME/.wdm"; do
    if [ -n "$dir" ] && [ -d "$dir" ]; then
        size=$(du -sh "$dir" 2>/dev/null | cut -f1 || echo "unknown")
        files=$(find "$dir" -type f 2>/dev/null | wc -l || echo "unknown")
        log_info "  $dir: exists, size=$size, files=$files"
    else
        log_info "  $dir: does not exist"
    fi
done

# Check if Playwright is installed
if command_exists playwright; then
    log_info "Playwright version: $(playwright --version 2>/dev/null || echo 'unknown')"
    log_info "Playwright browsers status:"
    playwright install --dry-run chromium 2>&1 | head -5 || log_warn "Could not check Playwright status"
else
    log_warn "Playwright command not found"
fi

log_success "Cache debugging completed"