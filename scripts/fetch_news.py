#!/usr/bin/env python3
"""
Script to fetch news using pygooglenews and save to a JSON file.
This script can be run as a GitHub Action.
"""

import os
import json
import argparse
from datetime import datetime
import sys
from pathlib import Path

# Add the parent directory to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from app.news_service import NewsService


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Fetch news and save to a JSON file")
    
    # News type options
    parser.add_argument(
        "--type", 
        choices=["top", "topic", "search", "geo"],
        default="top",
        help="Type of news to fetch (default: top)"
    )
    
    # Options for specific news types
    parser.add_argument("--topic", help="Topic for topic headlines")
    parser.add_argument("--query", help="Query for search")
    parser.add_argument("--when", help="Time period for search (e.g., 1h, 1d)")
    parser.add_argument("--from-date", help="From date for search (YYYY-MM-DD)")
    parser.add_argument("--to-date", help="To date for search (YYYY-MM-DD)")
    parser.add_argument("--location", help="Location for geo news")
    
    # Output options
    parser.add_argument(
        "--output", 
        default="news_data.json",
        help="Output file path (default: news_data.json)"
    )
    
    # News service options
    parser.add_argument("--language", default="en", help="Language code (default: en)")
    parser.add_argument("--country", default="US", help="Country code (default: US)")
    
    return parser.parse_args()


def fetch_news(args):
    """Fetch news based on command line arguments"""
    # Initialize news service
    news_service = NewsService(lang=args.language, country=args.country)
    
    # Fetch news based on type
    if args.type == "top":
        news_data = news_service.get_top_news()
        news_type_info = "top news"
    
    elif args.type == "topic":
        if not args.topic:
            raise ValueError("Topic must be provided for topic headlines")
        news_data = news_service.get_topic_headlines(args.topic)
        news_type_info = f"topic: {args.topic}"
    
    elif args.type == "search":
        if not args.query:
            raise ValueError("Query must be provided for search")
        news_data = news_service.search_news(
            query=args.query,
            when=args.when,
            from_date=args.from_date,
            to_date=args.to_date
        )
        news_type_info = f"search: {args.query}"
    
    elif args.type == "geo":
        if not args.location:
            raise ValueError("Location must be provided for geo news")
        news_data = news_service.get_location_news(args.location)
        news_type_info = f"location: {args.location}"
    
    else:
        raise ValueError(f"Invalid news type: {args.type}")
    
    # Format news data
    formatted_data = news_service.format_news_data(news_data)
    
    # Add metadata
    result = {
        "metadata": {
            "type": args.type,
            "timestamp": datetime.now().isoformat(),
            "info": news_type_info,
            "count": len(formatted_data)
        },
        "articles": formatted_data
    }
    
    return result


def save_to_json(data, output_path):
    """Save data to a JSON file"""
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    # Save data to JSON file
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"News data saved to {output_path}")
    print(f"Found {data['metadata']['count']} articles")


def main():
    """Main function"""
    args = parse_args()
    
    try:
        # Fetch news
        news_data = fetch_news(args)
        
        # Save to JSON file
        save_to_json(news_data, args.output)
        
        return 0
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 