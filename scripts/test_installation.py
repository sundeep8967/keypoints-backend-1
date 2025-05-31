#!/usr/bin/env python3
"""
Test script to verify PyGoogleNews installation.
"""

import sys
import importlib.util
import pkg_resources

def check_module(module_name):
    """Check if a module is installed and can be imported."""
    try:
        spec = importlib.util.find_spec(module_name)
        if spec is None:
            print(f"❌ Module {module_name} is not installed")
            return False
        else:
            module = importlib.import_module(module_name)
            version = getattr(module, "__version__", "Unknown")
            print(f"✅ Module {module_name} is installed (version: {version})")
            return True
    except ImportError as e:
        print(f"❌ Error importing {module_name}: {e}")
        return False

def check_dependencies():
    """Check PyGoogleNews dependencies."""
    required_packages = {
        'feedparser': '6.0.0',
        'beautifulsoup4': '4.9.0'
    }
    
    all_ok = True
    print("\nChecking required dependencies:")
    for package, min_version in required_packages.items():
        try:
            installed_version = pkg_resources.get_distribution(package).version
            if pkg_resources.parse_version(installed_version) >= pkg_resources.parse_version(min_version):
                print(f"✅ {package} {installed_version} is installed (min: {min_version})")
            else:
                print(f"⚠️ {package} {installed_version} is installed but minimum {min_version} is required")
                all_ok = False
        except pkg_resources.DistributionNotFound:
            print(f"❌ {package} is not installed")
            all_ok = False
        except Exception as e:
            print(f"❌ Error checking {package}: {e}")
            all_ok = False
    
    return all_ok

def test_pygooglenews():
    """Test PyGoogleNews functionality."""
    try:
        from pygooglenews import GoogleNews
        gn = GoogleNews()
        print("\nTesting PyGoogleNews functionality:")
        print("Fetching top news (this might take a moment)...")
        top = gn.top_news()
        entries_count = len(top.get('entries', []))
        print(f"✅ Successfully fetched {entries_count} top news entries")
        return True
    except Exception as e:
        print(f"❌ Error testing PyGoogleNews: {e}")
        return False

def main():
    """Main function."""
    print("=== PyGoogleNews Installation Test ===\n")
    print(f"Python version: {sys.version}")
    
    # Check core modules
    modules_ok = all([
        check_module("pygooglenews"),
        check_module("feedparser"),
        check_module("bs4")  # beautifulsoup4
    ])
    
    # Check dependencies
    deps_ok = check_dependencies()
    
    # Test functionality
    func_ok = test_pygooglenews()
    
    # Overall status
    print("\n=== Summary ===")
    if modules_ok and deps_ok and func_ok:
        print("✅ All tests passed. PyGoogleNews is properly installed.")
        return 0
    else:
        print("❌ Some tests failed. See details above.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 