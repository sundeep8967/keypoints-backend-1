import sys
import logging
from typing import Dict, List, Optional, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("news_service")

# Attempt to import PyGoogleNews with better error handling
try:
    from pygooglenews import GoogleNews
    logger.info("Successfully imported PyGoogleNews")
except ImportError as e:
    logger.error(f"Failed to import PyGoogleNews: {e}")
    logger.error("Make sure pygooglenews, feedparser, and beautifulsoup4 are installed")
    try:
        # Try to check if dependencies are installed
        import pkg_resources
        for pkg in ['feedparser', 'beautifulsoup4']:
            try:
                version = pkg_resources.get_distribution(pkg).version
                logger.info(f"{pkg} version {version} is installed")
            except pkg_resources.DistributionNotFound:
                logger.error(f"{pkg} is not installed")
    except ImportError:
        logger.error("pkg_resources not available to check dependencies")
    
    # Re-raise the error to fail fast if PyGoogleNews can't be imported
    raise


class NewsService:
    def __init__(self, language: str = 'en', country: str = 'US'):
        """
        Initialize the NewsService with Google News
        
        Args:
            language (str): Language code (default: 'en')
            country (str): Country code (default: 'US')
        """
        try:
            self.gn = GoogleNews(lang=language, country=country)
            logger.info(f"Initialized GoogleNews with language={language}, country={country}")
        except Exception as e:
            logger.error(f"Failed to initialize GoogleNews: {e}")
            raise
    
    def get_top_news(self) -> Dict[str, Any]:
        """
        Get top news stories
        
        Returns:
            Dict[str, Any]: Dictionary containing feed and entries
        """
        try:
            result = self.gn.top_news()
            entries_count = len(result.get('entries', []))
            logger.info(f"Retrieved {entries_count} top news entries")
            return result
        except Exception as e:
            logger.error(f"Error getting top news: {e}")
            raise
    
    def get_topic_headlines(self, topic: str) -> Dict[str, Any]:
        """
        Get headlines for a specific topic
        
        Args:
            topic (str): Topic to search for (business, technology, entertainment, sports, health, science, world)
            
        Returns:
            Dict[str, Any]: Dictionary containing feed and entries
        """
        try:
            result = self.gn.topic_headlines(topic)
            entries_count = len(result.get('entries', []))
            logger.info(f"Retrieved {entries_count} entries for topic '{topic}'")
            return result
        except Exception as e:
            logger.error(f"Error getting topic headlines for '{topic}': {e}")
            raise
    
    def search_news(self, 
                   query: str, 
                   when: Optional[str] = None,
                   from_date: Optional[str] = None, 
                   to_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Search for news with a specific query
        
        Args:
            query (str): Search query
            when (Optional[str]): Time period for search (e.g., '1h', '1d', '7d', '1m')
            from_date (Optional[str]): Start date in format 'YYYY-MM-DD'
            to_date (Optional[str]): End date in format 'YYYY-MM-DD'
            
        Returns:
            Dict[str, Any]: Dictionary containing feed and entries
        """
        try:
            result = self.gn.search(query, when=when, from_=from_date, to_=to_date)
            entries_count = len(result.get('entries', []))
            logger.info(f"Retrieved {entries_count} entries for search query '{query}'")
            return result
        except Exception as e:
            logger.error(f"Error searching for news with query '{query}': {e}")
            raise
    
    def get_location_news(self, location: str) -> Dict[str, Any]:
        """
        Get news for a specific location/geo
        
        Args:
            location (str): Location to get news for
            
        Returns:
            Dict[str, Any]: Dictionary containing feed and entries
        """
        try:
            result = self.gn.geo(location)
            entries_count = len(result.get('entries', []))
            logger.info(f"Retrieved {entries_count} entries for location '{location}'")
            return result
        except Exception as e:
            logger.error(f"Error getting news for location '{location}': {e}")
            raise
    
    def format_news_data(self, news_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Format news data into a more usable structure
        
        Args:
            news_data (Dict[str, Any]): Raw news data from GoogleNews
            
        Returns:
            List[Dict[str, Any]]: Formatted list of news articles
        """
        formatted_articles = []
        
        for entry in news_data.get('entries', []):
            article = {
                'title': entry.get('title'),
                'link': entry.get('link'),
                'published': entry.get('published'),
                'published_parsed': entry.get('published_parsed'),
                'source': entry.get('source', {}).get('title') if entry.get('source') else None,
                'sub_articles': entry.get('sub_articles', [])
            }
            formatted_articles.append(article)
        
        logger.info(f"Formatted {len(formatted_articles)} articles")
        return formatted_articles 