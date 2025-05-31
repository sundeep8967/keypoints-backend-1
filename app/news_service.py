from pygooglenews import GoogleNews
from typing import Dict, List, Optional, Any


class NewsService:
    def __init__(self, language: str = 'en', country: str = 'US'):
        """
        Initialize the NewsService with Google News
        
        Args:
            language (str): Language code (default: 'en')
            country (str): Country code (default: 'US')
        """
        self.gn = GoogleNews(lang=language, country=country)
    
    def get_top_news(self) -> Dict[str, Any]:
        """
        Get top news stories
        
        Returns:
            Dict[str, Any]: Dictionary containing feed and entries
        """
        return self.gn.top_news()
    
    def get_topic_headlines(self, topic: str) -> Dict[str, Any]:
        """
        Get headlines for a specific topic
        
        Args:
            topic (str): Topic to search for (business, technology, entertainment, sports, health, science, world)
            
        Returns:
            Dict[str, Any]: Dictionary containing feed and entries
        """
        return self.gn.topic_headlines(topic)
    
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
        return self.gn.search(query, when=when, from_=from_date, to_=to_date)
    
    def get_location_news(self, location: str) -> Dict[str, Any]:
        """
        Get news for a specific location/geo
        
        Args:
            location (str): Location to get news for
            
        Returns:
            Dict[str, Any]: Dictionary containing feed and entries
        """
        return self.gn.geo(location)
    
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
            
        return formatted_articles 