from fastapi import FastAPI, Query, HTTPException
from typing import Dict, List, Optional, Any
import os
from dotenv import load_dotenv

from .news_service import NewsService

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="News API",
    description="API for fetching news using PyGoogleNews",
    version="1.0.0",
)

# Initialize NewsService
news_service = NewsService(
    language=os.getenv("NEWS_LANGUAGE", "en"),
    country=os.getenv("NEWS_COUNTRY", "US")
)


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "News API is running",
        "docs": "/docs",
        "endpoints": [
            "/top-news",
            "/topic-headlines/{topic}",
            "/search",
            "/geo/{location}"
        ]
    }


@app.get("/top-news", response_model=List[Dict[str, Any]])
async def get_top_news():
    """Get top news stories"""
    try:
        news_data = news_service.get_top_news()
        return news_service.format_news_data(news_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching top news: {str(e)}")


@app.get("/topic-headlines/{topic}", response_model=List[Dict[str, Any]])
async def get_topic_headlines(topic: str):
    """
    Get headlines for a specific topic
    
    Valid topics: business, technology, entertainment, sports, health, science, world
    """
    valid_topics = ["business", "technology", "entertainment", 
                   "sports", "health", "science", "world"]
    
    if topic.lower() not in valid_topics:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid topic. Choose from: {', '.join(valid_topics)}"
        )
    
    try:
        news_data = news_service.get_topic_headlines(topic)
        return news_service.format_news_data(news_data)
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error fetching headlines for topic '{topic}': {str(e)}"
        )


@app.get("/search", response_model=List[Dict[str, Any]])
async def search_news(
    query: str = Query(..., description="Search query"),
    when: Optional[str] = Query(None, description="Time period (e.g., 1h, 1d, 7d, 1m)"),
    from_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    """Search for news with a specific query"""
    try:
        news_data = news_service.search_news(
            query=query,
            when=when,
            from_date=from_date,
            to_date=to_date
        )
        return news_service.format_news_data(news_data)
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error searching for news with query '{query}': {str(e)}"
        )


@app.get("/geo/{location}", response_model=List[Dict[str, Any]])
async def get_location_news(location: str):
    """Get news for a specific location"""
    try:
        news_data = news_service.get_location_news(location)
        return news_service.format_news_data(news_data)
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error fetching news for location '{location}': {str(e)}"
        ) 