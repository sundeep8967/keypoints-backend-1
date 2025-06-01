"""
News service module using PyGoogleNews
"""
import logging
from typing import Dict, List, Optional
from pygooglenews import GoogleNews

logger = logging.getLogger(__name__)

class NewsService:
    def __init__(self, lang: str = 'en', country: str = 'US'):
        """Initialize the news service with language and country settings."""
        try:
            self.gn = GoogleNews(lang=lang, country=country)
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

    def search_news(self, query: str, when: Optional[str] = None) -> Dict:
        """Search for news with a specific query."""
        try:
            result = self.gn.search(query, when=when)
            logger.info(f"Successfully searched news for query: {query}")
            return result
        except Exception as e:
            logger.error(f"Error searching news for query {query}: {e}")
            raise

    def get_geo_news(self, location: str) -> Dict:
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