#!/bin/bash
# Script to optimize caching strategy
# Used by GitHub Actions workflow

# Source error handler
source "$(dirname "$0")/error_handler.sh"

log_info "🚀 Optimizing caching strategy..."

# Set cache directories
export PIP_CACHE_DIR="${PIP_CACHE_DIR:-$HOME/.pip-cache}"
export PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH:-$HOME/pw-browsers}"
export NLTK_DATA="${NLTK_DATA:-$HOME/nltk_data}"

# Create cache directories if they don't exist
mkdir -p "$PIP_CACHE_DIR"
mkdir -p "$PLAYWRIGHT_BROWSERS_PATH"
mkdir -p "$NLTK_DATA"

# Display cache information
log_info "Cache directories:"
log_info "  PIP_CACHE_DIR: $PIP_CACHE_DIR"
log_info "  PLAYWRIGHT_BROWSERS_PATH: $PLAYWRIGHT_BROWSERS_PATH"
log_info "  NLTK_DATA: $NLTK_DATA"

# Check cache sizes
if command_exists du; then
    log_info "Cache sizes:"
    [ -d "$PIP_CACHE_DIR" ] && log_info "  Pip cache: $(du -sh "$PIP_CACHE_DIR" 2>/dev/null | cut -f1 || echo 'N/A')"
    [ -d "$PLAYWRIGHT_BROWSERS_PATH" ] && log_info "  Playwright cache: $(du -sh "$PLAYWRIGHT_BROWSERS_PATH" 2>/dev/null | cut -f1 || echo 'N/A')"
    [ -d "$NLTK_DATA" ] && log_info "  NLTK cache: $(du -sh "$NLTK_DATA" 2>/dev/null | cut -f1 || echo 'N/A')"
fi

log_success "Caching optimization completed"