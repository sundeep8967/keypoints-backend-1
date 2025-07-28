#!/bin/bash
# Script to validate environment and dependencies
# Used by GitHub Actions workflow

# Source error handler
source "$(dirname "$0")/error_handler.sh"

log_info "🔍 Validating environment and dependencies..."

# Check Python version
log_info "Python version: $(python --version)"
log_info "Pip version: $(pip --version)"

# Check if required environment variables are set
if [ -n "$SUPABASE_URL" ] && [ -n "$SUPABASE_KEY" ]; then
    log_success "Supabase environment variables are set"
else
    log_warn "Supabase environment variables not set (will skip Supabase operations)"
fi

# Validate key Python imports
log_info "🔍 Validating Python imports..."
python scripts/verify_imports.py

# Check if data directory exists
if [ ! -d "data" ]; then
    log_info "📁 Creating data directory..."
    mkdir -p data
fi

# List installed packages for debugging
log_info "📦 Key installed packages:"
pip list | grep -E "(selenium|nltk|newspaper|pygooglenews|webdriver-manager|playwright|fastapi|uvicorn)" || log_info "Package listing completed"

log_success "Environment validation completed successfully"