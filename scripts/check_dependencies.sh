#!/bin/bash
# Script to check and install dependencies with proper error handling
# Used by GitHub Actions workflow
# shellcheck source=scripts/error_handler.sh

# Source error handler
source "$(dirname "$0")/error_handler.sh"

log_info "🔍 Checking and installing dependencies..."

# Show Python and pip versions for debugging
log_info "Python version: $(python --version)"
log_info "Pip version: $(pip --version)"

# Upgrade pip and install wheel for faster builds
log_info "Upgrading pip and installing wheel..."
retry_command 3 2 pip install --upgrade pip wheel

# Install all dependencies from requirements file
log_info "Installing dependencies from requirements.txt..."
if [ -f "requirements.txt" ]; then
    retry_command 3 5 pip install --cache-dir "${PIP_CACHE_DIR:-/tmp/pip-cache}" -r requirements.txt
    log_success "Dependencies installed successfully"
else
    log_error "requirements.txt not found"
    exit 1
fi

# Setup NLTK data
log_info "Setting up NLTK data..."
python scripts/setup_nltk.py

# Install Playwright for better performance
log_info "Installing Playwright..."
retry_command 3 5 pip install --cache-dir "${PIP_CACHE_DIR:-/tmp/pip-cache}" playwright

log_success "All dependencies installed successfully"