"""
News service module using PyGoogleNews
"""
import logging
import sys
import os
from pathlib import Path
from typing import Dict, List, Optional

# Add the parent directory to sys.path to find pygooglenews_module
sys.path.append(str(Path(__file__).parent.parent))

from pygooglenews_module import GoogleNews

# Summarizer removed - no longer needed

logger = logging.getLogger(__name__)

class NewsService:
    def __init__(self, lang: str = 'en', country: str = 'US', enable_optimizations: bool = True):
        """Initialize the news service with language and country settings."""
        try:
            self.gn = GoogleNews(lang=lang, country=country)
            self.enable_optimizations = enable_optimizations
            
            # PERFORMANCE OPTIMIZATION: Initialize connection session for reuse
            if enable_optimizations:
                import requests
                from requests.adapters import HTTPAdapter
                from urllib3.util.retry import Retry
                
                self.session = requests.Session()
                
                # Configure retry strategy for better reliability
                retry_strategy = Retry(
                    total=3,
                    backoff_factor=0.3,
                    status_forcelist=[429, 500, 502, 503, 504],
                )
                
                # Configure HTTP adapter with connection pooling
                adapter = HTTPAdapter(
                    pool_connections=10,
                    pool_maxsize=20,
                    max_retries=retry_strategy
                )
                
                self.session.mount("http://", adapter)
                self.session.mount("https://", adapter)
                
                logger.info(f"🚀 OPTIMIZED NewsService initialized with lang={lang}, country={country}")
            else:
                self.session = None
                logger.info(f"NewsService initialized with lang={lang}, country={country}")
                
        except Exception as e:
            logger.error(f"Failed to initialize GoogleNews: {e}")
            raise

    def get_top_news(self) -> Dict:
        """Get top news stories."""
        try:
            result = self.gn.top_news()
            logger.info("Successfully fetched top news")
            return result
        except Exception as e:
            logger.error(f"Error fetching top news: {e}")
            raise

    def get_topic_headlines(self, topic: str) -> Dict:
        """Get headlines for a specific topic."""
        try:
            result = self.gn.topic_headlines(topic)
            logger.info(f"Successfully fetched headlines for topic: {topic}")
            return result
        except Exception as e:
            logger.error(f"Error fetching topic headlines for {topic}: {e}")
            raise

    def search_news(self, query: str, when: Optional[str] = None, from_date: Optional[str] = None, to_date: Optional[str] = None) -> Dict:
        """Search for news with a specific query."""
        try:
            result = self.gn.search(query, when=when, from_=from_date, to_=to_date)
            logger.info(f"Successfully searched news for query: {query}")
            return result
        except Exception as e:
            logger.error(f"Error searching news for query {query}: {e}")
            raise

    def get_location_news(self, location: str) -> Dict:
        """Get news for a specific location."""
        try:
            result = self.gn.geo_headlines(location)
            logger.info(f"Successfully fetched geo news for location: {location}")
            return result
        except Exception as e:
            logger.error(f"Error fetching geo news for {location}: {e}")
            raise

    def extract_articles(self, news_data: Dict) -> List[Dict]:
        """Extract articles from news data."""
        articles = []
        try:
            if 'entries' in news_data:
                for entry in news_data['entries']:
                    article = {
                        'title': entry.get('title', ''),
                        'link': entry.get('link', ''),
                        'published': entry.get('published', ''),
                        'summary': entry.get('summary', ''),
                        'source': entry.get('source', {}).get('title', '') if entry.get('source') else ''
                    }
                    articles.append(article)
            logger.info(f"Extracted {len(articles)} articles")
        except Exception as e:
            logger.error(f"Error extracting articles: {e}")
        
        return articles
        
    def format_news_data(self, news_data: Dict, include_summary: bool = False, inshorts_style: bool = False) -> List[Dict]:
        """
        Format news data into a standardized structure.
        
        Args:
            news_data: Raw news data from GoogleNews
            include_summary: Whether to include AI-generated summaries
            inshorts_style: Whether to format summaries in Inshorts style
            
        Returns:
            List of formatted articles
        """
        formatted_data = []
        try:
            if 'entries' in news_data:
                for entry in news_data['entries']:
                    article = {
                        'title': entry.get('title'),
                        'link': entry.get('link'),
                        'published': entry.get('published'),
                        'published_parsed': entry.get('published_parsed'),
                        'source': entry.get('source', {}).get('title') if entry.get('source') else None,
                        'sub_articles': entry.get('sub_articles', [])
                    }
                    
                    # AI summary functionality removed
                    if include_summary:
                        article['ai_summary'] = "AI summarization not available"
                    
                    formatted_data.append(article)
            logger.info(f"Formatted {len(formatted_data)} articles")
        except Exception as e:
            logger.error(f"Error formatting news data: {e}")
        
        return formatted_data


# CLI functionality (moved from scripts/fetch_news.py)
if __name__ == "__main__":
    import os
    import json
    import argparse
    from datetime import datetime
    import sys
    
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

    sys.exit(main())