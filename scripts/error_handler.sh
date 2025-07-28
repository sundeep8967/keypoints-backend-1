#!/bin/bash
# Global error handler for all scripts
# Source this file in other scripts for consistent error handling

# Function to log with timestamp and level
log() {
    local level="$1"
    shift
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $*"
}

# Function to log info messages
log_info() {
    log "INFO" "$@"
}

# Function to log warning messages
log_warn() {
    log "WARN" "$@"
}

# Function to log error messages
log_error() {
    log "ERROR" "$@"
}

# Function to log success messages
log_success() {
    log "SUCCESS" "$@"
}

# Function to handle errors and exit gracefully
handle_error() {
    local exit_code=$?
    local line_number=$1
    log_error "Script failed at line $line_number with exit code $exit_code"
    log_error "Command: ${BASH_COMMAND}"
    exit $exit_code
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to retry a command with exponential backoff
retry_command() {
    local max_attempts="$1"
    local delay="$2"
    shift 2
    local attempt=1
    
    while [ "$attempt" -le "$max_attempts" ]; do
        if "$@"; then
            return 0
        fi
        
        if [ "$attempt" -eq "$max_attempts" ]; then
            log_error "Command failed after $max_attempts attempts: $*"
            return 1
        fi
        
        log_warn "Attempt $attempt failed, retrying in ${delay}s..."
        sleep "$delay"
        delay=$((delay * 2))  # Exponential backoff
        attempt=$((attempt + 1))
    done
}

# Set up error handling
set -eE  # Exit on error and inherit ERR trap
trap 'handle_error $LINENO' ERR