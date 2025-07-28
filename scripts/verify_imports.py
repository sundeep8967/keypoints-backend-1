#!/usr/bin/env python3
"""
Script to verify that all required imports work correctly.
Used by GitHub Actions workflow.
"""

try:
    import pygooglenews
    import selenium
    import nltk
    try:
        import playwright
        print('SUCCESS: All dependencies including Playwright imported successfully')
    except ImportError:
        print('SUCCESS: Core dependencies imported (Playwright not available, will use Selenium)')
except ImportError as e:
    print(f'ERROR: Import error: {e}')
    exit(1)