#!/bin/bash
# Script to install required dependencies for PyGoogleNews

# Exit on error
set -e

echo "Installing PyGoogleNews and its dependencies..."

# Install core dependencies first with correct versions
pip install "feedparser>=5.2.1,<6.0.0" "beautifulsoup4>=4.9.0"

# Install PyGoogleNews
pip install pygooglenews

# Verify installation
echo "Verifying installation..."
python -c "import feedparser; print(f'Feedparser version: {feedparser.__version__}')"
python -c "import pygooglenews; from pygooglenews import GoogleNews; print('✓ PyGoogleNews successfully imported')"

echo "Installation completed!" 