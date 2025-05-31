#!/bin/bash
# Script to install required dependencies for PyGoogleNews

# Exit on error
set -e

echo "Installing PyGoogleNews and its dependencies..."

# Install core dependencies first
pip install feedparser>=6.0.0 beautifulsoup4>=4.9.0

# Install PyGoogleNews
pip install pygooglenews

# Verify installation
echo "Verifying installation..."
python -c "import pygooglenews; from pygooglenews import GoogleNews; print('✓ PyGoogleNews successfully imported')"

echo "Installation completed!" 