#!/usr/bin/env python3
"""
Test script to verify all installations are working correctly.
"""
import sys
import traceback

def test_imports():
    """Test all required imports."""
    tests = []
    
    # Test pygooglenews
    try:
        import pygooglenews
        from pygooglenews import GoogleNews
        tests.append(("pygooglenews", "✅ PASS"))
    except Exception as e:
        tests.append(("pygooglenews", f"❌ FAIL: {e}"))
    
    # Test feedparser
    try:
        import feedparser
        tests.append(("feedparser", f"✅ PASS (version: {feedparser.__version__})"))
    except Exception as e:
        tests.append(("feedparser", f"❌ FAIL: {e}"))
    
    # Test beautifulsoup4
    try:
        from bs4 import BeautifulSoup
        tests.append(("beautifulsoup4", "✅ PASS"))
    except Exception as e:
        tests.append(("beautifulsoup4", f"❌ FAIL: {e}"))
    
    # Test fastapi
    try:
        import fastapi
        tests.append(("fastapi", "✅ PASS"))
    except Exception as e:
        tests.append(("fastapi", f"❌ FAIL: {e}"))
    
    # Test requests
    try:
        import requests
        tests.append(("requests", "✅ PASS"))
    except Exception as e:
        tests.append(("requests", f"❌ FAIL: {e}"))
    
    return tests

def test_googlenews_functionality():
    """Test basic GoogleNews functionality."""
    try:
        from pygooglenews import GoogleNews
        gn = GoogleNews(lang='en', country='US')
        
        # Test top news (just check if it doesn't crash)
        result = gn.top_news()
        if 'entries' in result:
            return "✅ PASS - GoogleNews functionality working"
        else:
            return "⚠️  WARNING - GoogleNews returned unexpected format"
    except Exception as e:
        return f"❌ FAIL - GoogleNews functionality: {e}"

def main():
    """Run all tests."""
    print("🔍 Testing installation...")
    print("=" * 50)
    
    # Test imports
    print("📦 Testing imports:")
    import_tests = test_imports()
    failed_imports = 0
    
    for package, result in import_tests:
        print(f"  {package}: {result}")
        if "FAIL" in result:
            failed_imports += 1
    
    print()
    
    # Test functionality
    print("🚀 Testing functionality:")
    functionality_result = test_googlenews_functionality()
    print(f"  GoogleNews: {functionality_result}")
    
    print("=" * 50)
    
    # Summary
    if failed_imports > 0:
        print(f"❌ {failed_imports} import(s) failed!")
        sys.exit(1)
    elif "FAIL" in functionality_result:
        print("❌ Functionality test failed!")
        sys.exit(1)
    else:
        print("✅ All tests passed!")
        sys.exit(0)

if __name__ == "__main__":
    main()