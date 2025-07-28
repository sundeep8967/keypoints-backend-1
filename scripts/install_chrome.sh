#!/bin/bash
# Script to install Chrome for Selenium
# Used by GitHub Actions workflow
# shellcheck source=scripts/error_handler.sh

# Source error handler
source "$(dirname "$0")/error_handler.sh"

log_info "Setting up Chrome for Selenium..."

# Check if Chrome is already installed
if command_exists google-chrome; then
    log_success "Chrome already installed: $(google-chrome --version)"
    exit 0
fi

log_info "📥 Installing Chrome for Selenium..."

# Add Google Chrome repository
retry_command 3 2 wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
sudo sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'

# Update package list and install Chrome
retry_command 3 5 sudo apt-get update
retry_command 3 5 sudo apt-get install -y google-chrome-stable

# Verify installation
if command_exists google-chrome; then
    log_success "Chrome installed successfully: $(google-chrome --version)"
else
    log_error "Chrome installation failed"
    exit 1
fi