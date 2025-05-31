#!/usr/bin/env python3
"""
Simple test script to verify PyGoogleNews is working.
"""

from pygooglenews import GoogleNews

def main():
    """Run a simple test."""
    print("Initializing GoogleNews...")
    gn = GoogleNews(lang='en', country='US')
    
    print("Fetching top news...")
    top = gn.top_news()
    
    print(f"Retrieved {len(top.get('entries', []))} top news entries")
    
    # Print the first entry
    if top.get('entries'):
        first = top['entries'][0]
        print("\nFirst article:")
        print(f"Title: {first.get('title')}")
        print(f"Link: {first.get('link')}")
        print(f"Published: {first.get('published')}")
        
    print("\nTest completed successfully!")

if __name__ == "__main__":
    main() 