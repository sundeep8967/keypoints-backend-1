#!/bin/bash
# Script to check which browser automation is available
# shellcheck source=scripts/error_handler.sh

# Source error handler
source "$(dirname "$0")/error_handler.sh"

log_info "🔍 Checking browser automation setup..."

# Set environment variables
export PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH:-$HOME/pw-browsers}"

# Check for Playwright
if [ -f "$PLAYWRIGHT_BROWSERS_PATH/.playwright_ready" ]; then
    log_success "Playwright is available and ready"
    if command_exists playwright; then
        playwright_version=$(playwright --version 2>/dev/null || echo "unknown")
        log_info "Playwright version: $playwright_version"
        echo "BROWSER_ENGINE=playwright" >> "$GITHUB_ENV" 2>/dev/null || true
        exit 0
    else
        log_warn "Playwright marker found but command not available"
        rm -f "$PLAYWRIGHT_BROWSERS_PATH/.playwright_ready"
    fi
fi

# Check for Selenium fallback
if [ -f "$PLAYWRIGHT_BROWSERS_PATH/.selenium_fallback" ]; then
    log_success "Selenium fallback is configured"
    echo "BROWSER_ENGINE=selenium" >> "$GITHUB_ENV" 2>/dev/null || true
    exit 0
fi

# Check if Playwright is available without markers
if command_exists playwright; then
    if playwright install --dry-run chromium >/dev/null 2>&1; then
        log_success "Playwright is available (no marker file)"
        touch "$PLAYWRIGHT_BROWSERS_PATH/.playwright_ready" 2>/dev/null || true
        echo "BROWSER_ENGINE=playwright" >> "$GITHUB_ENV" 2>/dev/null || true
        exit 0
    fi
fi

# Test Selenium as last resort
log_info "Testing Selenium availability..."
if command_exists python; then
    if python -c "
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

try:
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.get('https://www.google.com')
    driver.quit()
    print('Selenium is working')
    exit(0)
except Exception as e:
    print(f'Selenium test failed: {e}')
    exit(1)
" >/dev/null 2>&1; then
        log_success "Selenium is working"
        mkdir -p "$PLAYWRIGHT_BROWSERS_PATH"
        touch "$PLAYWRIGHT_BROWSERS_PATH/.selenium_fallback"
        echo "BROWSER_ENGINE=selenium" >> "$GITHUB_ENV" 2>/dev/null || true
        exit 0
    else
        log_error "Selenium test failed"
    fi
fi

log_error "No working browser automation found"
echo "BROWSER_ENGINE=none" >> "$GITHUB_ENV" 2>/dev/null || true
exit 1