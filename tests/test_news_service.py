import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add parent directory to path to import app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.news_service import NewsService


class TestNewsService(unittest.TestCase):
    """Tests for the NewsService class"""
    
    def setUp(self):
        """Set up before each test"""
        self.news_service = NewsService()
    
    @patch('app.news_service.GoogleNews')
    def test_init(self, mock_google_news):
        """Test the initialization of NewsService"""
        # Test with default parameters
        news_service = NewsService()
        mock_google_news.assert_called_once_with(lang='en', country='US')
        
        # Test with custom parameters
        news_service = NewsService(language='fr', country='FR')
        mock_google_news.assert_called_with(lang='fr', country='FR')
    
    @patch('app.news_service.GoogleNews')
    def test_get_top_news(self, mock_google_news):
        """Test get_top_news method"""
        # Mock the top_news method
        mock_instance = mock_google_news.return_value
        mock_instance.top_news.return_value = {'feed': {}, 'entries': []}
        
        # Call the method
        result = self.news_service.get_top_news()
        
        # Assert the result
        self.assertEqual(result, {'feed': {}, 'entries': []})
        mock_instance.top_news.assert_called_once()
    
    @patch('app.news_service.GoogleNews')
    def test_get_topic_headlines(self, mock_google_news):
        """Test get_topic_headlines method"""
        # Mock the topic_headlines method
        mock_instance = mock_google_news.return_value
        mock_instance.topic_headlines.return_value = {'feed': {}, 'entries': []}
        
        # Call the method
        result = self.news_service.get_topic_headlines('technology')
        
        # Assert the result
        self.assertEqual(result, {'feed': {}, 'entries': []})
        mock_instance.topic_headlines.assert_called_once_with('technology')
    
    @patch('app.news_service.GoogleNews')
    def test_search_news(self, mock_google_news):
        """Test search_news method"""
        # Mock the search method
        mock_instance = mock_google_news.return_value
        mock_instance.search.return_value = {'feed': {}, 'entries': []}
        
        # Call the method
        result = self.news_service.search_news(
            query='test',
            when='1d',
            from_date='2023-01-01',
            to_date='2023-01-02'
        )
        
        # Assert the result
        self.assertEqual(result, {'feed': {}, 'entries': []})
        mock_instance.search.assert_called_once_with(
            'test', when='1d', from_='2023-01-01', to_='2023-01-02'
        )
    
    @patch('app.news_service.GoogleNews')
    def test_get_location_news(self, mock_google_news):
        """Test get_location_news method"""
        # Mock the geo method
        mock_instance = mock_google_news.return_value
        mock_instance.geo.return_value = {'feed': {}, 'entries': []}
        
        # Call the method
        result = self.news_service.get_location_news('San Francisco')
        
        # Assert the result
        self.assertEqual(result, {'feed': {}, 'entries': []})
        mock_instance.geo.assert_called_once_with('San Francisco')
    
    def test_format_news_data(self):
        """Test format_news_data method"""
        # Mock news data
        news_data = {
            'feed': {},
            'entries': [
                {
                    'title': 'Test Article 1',
                    'link': 'https://example.com/1',
                    'published': '2023-01-01',
                    'published_parsed': (2023, 1, 1, 0, 0, 0, 0, 0, 0),
                    'source': {'title': 'Test Source'},
                    'sub_articles': []
                },
                {
                    'title': 'Test Article 2',
                    'link': 'https://example.com/2',
                    'published': '2023-01-02',
                    'published_parsed': (2023, 1, 2, 0, 0, 0, 0, 0, 0),
                    'source': {'title': 'Test Source'},
                    'sub_articles': []
                }
            ]
        }
        
        # Expected result
        expected = [
            {
                'title': 'Test Article 1',
                'link': 'https://example.com/1',
                'published': '2023-01-01',
                'published_parsed': (2023, 1, 1, 0, 0, 0, 0, 0, 0),
                'source': 'Test Source',
                'sub_articles': []
            },
            {
                'title': 'Test Article 2',
                'link': 'https://example.com/2',
                'published': '2023-01-02',
                'published_parsed': (2023, 1, 2, 0, 0, 0, 0, 0, 0),
                'source': 'Test Source',
                'sub_articles': []
            }
        ]
        
        # Call the method
        result = self.news_service.format_news_data(news_data)
        
        # Assert the result
        self.assertEqual(result, expected)
        
        # Test with missing fields
        news_data = {
            'feed': {},
            'entries': [
                {
                    'title': 'Test Article 3',
                    'link': 'https://example.com/3'
                }
            ]
        }
        
        expected = [
            {
                'title': 'Test Article 3',
                'link': 'https://example.com/3',
                'published': None,
                'published_parsed': None,
                'source': None,
                'sub_articles': []
            }
        ]
        
        result = self.news_service.format_news_data(news_data)
        self.assertEqual(result, expected)


if __name__ == '__main__':
    unittest.main() 