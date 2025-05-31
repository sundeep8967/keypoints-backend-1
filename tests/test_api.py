import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import sys
import os

# Add parent directory to path to import app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.api import app


class TestAPI(unittest.TestCase):
    """Tests for the API endpoints"""
    
    def setUp(self):
        """Set up before each test"""
        self.client = TestClient(app)
    
    def test_root(self):
        """Test the root endpoint"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "message": "News API is running",
            "docs": "/docs",
            "endpoints": [
                "/top-news",
                "/topic-headlines/{topic}",
                "/search",
                "/geo/{location}"
            ]
        })
    
    @patch('app.api.news_service')
    def test_get_top_news(self, mock_news_service):
        """Test the get_top_news endpoint"""
        # Mock the get_top_news method
        mock_news_service.get_top_news.return_value = {'feed': {}, 'entries': []}
        mock_news_service.format_news_data.return_value = []
        
        # Call the endpoint
        response = self.client.get("/top-news")
        
        # Assert the response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])
        mock_news_service.get_top_news.assert_called_once()
        mock_news_service.format_news_data.assert_called_once_with({'feed': {}, 'entries': []})
    
    @patch('app.api.news_service')
    def test_get_top_news_error(self, mock_news_service):
        """Test the get_top_news endpoint with an error"""
        # Mock the get_top_news method to raise an exception
        mock_news_service.get_top_news.side_effect = Exception("Test error")
        
        # Call the endpoint
        response = self.client.get("/top-news")
        
        # Assert the response
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), {"detail": "Error fetching top news: Test error"})
    
    @patch('app.api.news_service')
    def test_get_topic_headlines(self, mock_news_service):
        """Test the get_topic_headlines endpoint"""
        # Mock the get_topic_headlines method
        mock_news_service.get_topic_headlines.return_value = {'feed': {}, 'entries': []}
        mock_news_service.format_news_data.return_value = []
        
        # Call the endpoint
        response = self.client.get("/topic-headlines/technology")
        
        # Assert the response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])
        mock_news_service.get_topic_headlines.assert_called_once_with("technology")
        mock_news_service.format_news_data.assert_called_once_with({'feed': {}, 'entries': []})
    
    @patch('app.api.news_service')
    def test_get_topic_headlines_invalid_topic(self, mock_news_service):
        """Test the get_topic_headlines endpoint with an invalid topic"""
        # Call the endpoint with an invalid topic
        response = self.client.get("/topic-headlines/invalid")
        
        # Assert the response
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid topic", response.json()["detail"])
    
    @patch('app.api.news_service')
    def test_search_news(self, mock_news_service):
        """Test the search_news endpoint"""
        # Mock the search_news method
        mock_news_service.search_news.return_value = {'feed': {}, 'entries': []}
        mock_news_service.format_news_data.return_value = []
        
        # Call the endpoint
        response = self.client.get("/search?query=test&when=1d")
        
        # Assert the response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])
        mock_news_service.search_news.assert_called_once_with(
            query="test", when="1d", from_date=None, to_date=None
        )
        mock_news_service.format_news_data.assert_called_once_with({'feed': {}, 'entries': []})
    
    @patch('app.api.news_service')
    def test_search_news_full_params(self, mock_news_service):
        """Test the search_news endpoint with all parameters"""
        # Mock the search_news method
        mock_news_service.search_news.return_value = {'feed': {}, 'entries': []}
        mock_news_service.format_news_data.return_value = []
        
        # Call the endpoint
        response = self.client.get(
            "/search?query=test&when=1d&from_date=2023-01-01&to_date=2023-01-02"
        )
        
        # Assert the response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])
        mock_news_service.search_news.assert_called_once_with(
            query="test", when="1d", from_date="2023-01-01", to_date="2023-01-02"
        )
    
    @patch('app.api.news_service')
    def test_get_location_news(self, mock_news_service):
        """Test the get_location_news endpoint"""
        # Mock the get_location_news method
        mock_news_service.get_location_news.return_value = {'feed': {}, 'entries': []}
        mock_news_service.format_news_data.return_value = []
        
        # Call the endpoint
        response = self.client.get("/geo/San%20Francisco")
        
        # Assert the response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])
        mock_news_service.get_location_news.assert_called_once_with("San Francisco")
        mock_news_service.format_news_data.assert_called_once_with({'feed': {}, 'entries': []})


if __name__ == '__main__':
    unittest.main() 