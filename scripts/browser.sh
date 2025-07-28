#!/bin/bash
# Consolidated browser automation setup
# Handles Playwright → Selenium fallback logic

set -eE
trap 'echo "❌ Browser setup failed at line $LINENO"' ERR

# Logging functions
log_info() { echo "[$(date '+%H:%M:%S')] ℹ️  $*"; }
log_success() { echo "[$(date '+%H:%M:%S')] ✅ $*"; }
log_warn() { echo "[$(date '+%H:%M:%S')] ⚠️  $*"; }
log_error() { echo "[$(date '+%H:%M:%S')] ❌ $*"; }

# Environment setup
export PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH:-$HOME/pw-browsers}"
mkdir -p "$PLAYWRIGHT_BROWSERS_PATH"

log_info "🎭 Setting up browser automation..."

# Function to test Selenium
test_selenium() {
    python -c "
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
    print('Selenium working')
except Exception as e:
    print(f'Selenium failed: {e}')
    exit(1)
" >/dev/null 2>&1
}

# Try Playwright first
if [ -f "$PLAYWRIGHT_BROWSERS_PATH/.playwright_ready" ]; then
    log_success "Playwright already available"
    echo "BROWSER_ENGINE=playwright" >> "${GITHUB_ENV:-/dev/null}" 2>/dev/null || true
elif command -v playwright >/dev/null 2>&1; then
    log_info "Installing Playwright browsers..."
    if playwright install chromium --with-deps >/dev/null 2>&1 && playwright install --dry-run chromium >/dev/null 2>&1; then
        touch "$PLAYWRIGHT_BROWSERS_PATH/.playwright_ready"
        log_success "Playwright setup successful"
        echo "BROWSER_ENGINE=playwright" >> "${GITHUB_ENV:-/dev/null}" 2>/dev/null || true
    else
        log_warn "Playwright installation failed, trying Selenium..."
        rm -rf "$PLAYWRIGHT_BROWSERS_PATH"
        mkdir -p "$PLAYWRIGHT_BROWSERS_PATH"
        if test_selenium; then
            touch "$PLAYWRIGHT_BROWSERS_PATH/.selenium_fallback"
            log_success "Selenium fallback configured"
            echo "BROWSER_ENGINE=selenium" >> "${GITHUB_ENV:-/dev/null}" 2>/dev/null || true
        else
            log_error "Both Playwright and Selenium failed"
            echo "BROWSER_ENGINE=none" >> "${GITHUB_ENV:-/dev/null}" 2>/dev/null || true
            exit 1
        fi
    fi
else
    log_warn "Playwright not available, using Selenium..."
    if test_selenium; then
        touch "$PLAYWRIGHT_BROWSERS_PATH/.selenium_fallback"
        log_success "Selenium configured"
        echo "BROWSER_ENGINE=selenium" >> "${GITHUB_ENV:-/dev/null}" 2>/dev/null || true
    else
        log_error "Selenium setup failed"
        echo "BROWSER_ENGINE=none" >> "${GITHUB_ENV:-/dev/null}" 2>/dev/null || true
        exit 1
    fi
fi

log_success "🎉 Browser automation ready!"