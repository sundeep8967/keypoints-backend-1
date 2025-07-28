#!/bin/bash
# Consolidated setup script - replaces multiple scattered scripts
# Handles dependencies, environment, caching, and Chrome installation

set -eE
trap 'echo "❌ Setup failed at line $LINENO"' ERR

# Logging functions
log_info() { echo "[$(date '+%H:%M:%S')] ℹ️  $*"; }
log_success() { echo "[$(date '+%H:%M:%S')] ✅ $*"; }
log_warn() { echo "[$(date '+%H:%M:%S')] ⚠️  $*"; }
log_error() { echo "[$(date '+%H:%M:%S')] ❌ $*"; }

# Retry function
retry_cmd() {
    local max_attempts=3
    local delay=2
    local attempt=1
    
    while [ "$attempt" -le "$max_attempts" ]; do
        if "$@"; then return 0; fi
        if [ "$attempt" -eq "$max_attempts" ]; then
            log_error "Command failed after $max_attempts attempts: $*"
            return 1
        fi
        log_warn "Attempt $attempt failed, retrying in ${delay}s..."
        sleep "$delay"
        delay=$((delay * 2))
        attempt=$((attempt + 1))
    done
}

log_info "🚀 Starting consolidated setup..."

# 1. Setup cache directories
log_info "📁 Setting up cache directories..."
export PIP_CACHE_DIR="${PIP_CACHE_DIR:-$HOME/.pip-cache}"
export PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH:-$HOME/pw-browsers}"
mkdir -p "$PIP_CACHE_DIR" "$PLAYWRIGHT_BROWSERS_PATH" "$HOME/nltk_data"

# 2. Install Python dependencies
log_info "📦 Installing Python dependencies..."
retry_cmd pip install --upgrade pip wheel
retry_cmd pip install --cache-dir "$PIP_CACHE_DIR" -r requirements.txt

# 3. Setup NLTK data
log_info "📚 Setting up NLTK data..."
python -c "
import nltk
import os
nltk_data_dir = os.path.expanduser('~/nltk_data')
if not os.path.exists(os.path.join(nltk_data_dir, 'tokenizers', 'punkt')):
    nltk.download('punkt', download_dir=nltk_data_dir)
else:
    print('NLTK data already available')
"

# 4. Install Chrome if needed
log_info "🌐 Setting up Chrome..."
if command -v google-chrome >/dev/null 2>&1; then
    log_success "Chrome already installed: $(google-chrome --version)"
else
    log_info "Installing Chrome..."
    retry_cmd wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
    sudo sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'
    retry_cmd sudo apt-get update
    retry_cmd sudo apt-get install -y google-chrome-stable
    log_success "Chrome installed: $(google-chrome --version)"
fi

# 5. Validate environment
log_info "🔍 Validating environment..."
python -c "
try:
    import pygooglenews, selenium, nltk, fastapi
    print('✅ All core imports successful')
except ImportError as e:
    print(f'❌ Import error: {e}')
    exit(1)
"

# 6. Check Supabase environment
if [ -n "$SUPABASE_URL" ] && [ -n "$SUPABASE_KEY" ]; then
    log_success "Supabase environment configured"
else
    log_warn "Supabase environment not configured (will skip database operations)"
fi

log_success "🎉 Setup completed successfully!"