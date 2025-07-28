"""
News service module using PyGoogleNews
"""
import logging
from typing import Dict, List, Optional
from pygooglenews_module import GoogleNews

# Make summarizer import optional to avoid dependency issues
try:
    from app.summarizer import NewsSummarizer
    SUMMARIZER_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Summarizer not available due to missing dependencies: {e}")
    SUMMARIZER_AVAILABLE = False
    NewsSummarizer = None

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
                    
                    # Add AI-generated summary if requested
                    if include_summary and article['link'] and SUMMARIZER_AVAILABLE:
                        try:
                            summary = NewsSummarizer.summarize_from_url(article['link'])
                            if summary and inshorts_style:
                                summary = NewsSummarizer.format_inshorts_style(
                                    article['title'], summary
                                )
                            article['ai_summary'] = summary
                        except Exception as e:
                            logger.error(f"Error generating summary: {e}")
                            article['ai_summary'] = None
                    elif include_summary and not SUMMARIZER_AVAILABLE:
                        article['ai_summary'] = "Summarizer not available - missing dependencies"
                    
                    formatted_data.append(article)
            logger.info(f"Formatted {len(formatted_data)} articles")
        except Exception as e:
            logger.error(f"Error formatting news data: {e}")
        
        return formatted_data