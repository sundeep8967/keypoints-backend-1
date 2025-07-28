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
    # Verify browsers are actually functional
    if playwright install --dry-run chromium >/dev/null 2>&1; then
        log_success "Cached browsers are valid"
        exit 0
    else
        log_warn "Cached browsers are invalid, reinstalling..."
        rm -rf "$PLAYWRIGHT_BROWSERS_PATH"
    fi
fi

log_info "📥 Installing Playwright browsers (will be cached for next run)"

# Create browsers directory
mkdir -p "$PLAYWRIGHT_BROWSERS_PATH"

# Install Playwright browsers with retry
if retry_command 3 10 playwright install chromium --with-deps; then
    log_success "Playwright browsers installed successfully"
    # Verify installation
    if playwright install --dry-run chromium >/dev/null 2>&1; then
        log_success "Playwright installation verified"
        # Create a marker file to indicate Playwright is available
        touch "$PLAYWRIGHT_BROWSERS_PATH/.playwright_ready"
        exit 0
    else
        log_warn "Playwright installation verification failed, removing installation"
        rm -rf "$PLAYWRIGHT_BROWSERS_PATH"
    fi
fi

# If we reach here, Playwright installation failed
log_error "Playwright installation failed completely"
log_info "Setting up Selenium fallback..."

# Ensure Selenium WebDriver is properly set up
if command_exists python; then
    python -c "
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

try:
    # Set up Chrome options for headless mode
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    # Install and set up ChromeDriver
    service = Service(ChromeDriverManager().install())
    
    # Test Selenium setup
    driver = webdriver.Chrome(service=service, options=options)
    driver.get('https://www.google.com')
    driver.quit()
    
    print('✅ Selenium fallback setup successful')
except Exception as e:
    print(f'❌ Selenium fallback setup failed: {e}')
    exit(1)
"
    if [ $? -eq 0 ]; then
        log_success "Selenium fallback configured successfully"
        # Create marker file to indicate Selenium is the fallback
        mkdir -p "$PLAYWRIGHT_BROWSERS_PATH"
        touch "$PLAYWRIGHT_BROWSERS_PATH/.selenium_fallback"
        exit 0
    else
        log_error "Both Playwright and Selenium setup failed"
        exit 1
    fi
else
    log_error "Python not available for Selenium fallback"
    exit 1
fi