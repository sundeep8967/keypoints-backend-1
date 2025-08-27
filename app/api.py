from fastapi import FastAPI, Query, HTTPException
from typing import Dict, List, Optional, Any
import os
from dotenv import load_dotenv

from .news_service import NewsService
from .db import (
    store_news, get_stored_news, search_news_in_db, get_categories_stats,
    get_trending_articles, get_articles_by_source, get_popular_sources,
    cleanup_old_articles
)

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
    lang=os.getenv("NEWS_LANGUAGE", "en"),
    country=os.getenv("NEWS_COUNTRY", "US")
)


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "News API with Supabase is running",
        "docs": "/docs",
        "endpoints": [
            "/top-news",
            "/topic-headlines/{topic}",
            "/search",
            "/geo/{location}",
            "/supabase/stats"
        ],
        "features": [
            "Supabase caching",
            "Real-time data storage",
            "Search functionality"
        ]
    }


@app.get("/top-news", response_model=List[Dict[str, Any]])
async def get_top_news(use_cache: bool = Query(True, description="Use cached news if available")):
    """Get top news stories with optional caching"""
    try:
        if use_cache:
            # Try to get cached news first
            cached_news = await get_stored_news(category="top")
            if cached_news:
                return cached_news

        # Fetch fresh news if cache is disabled or empty
        news_data = news_service.get_top_news()
        formatted_news = news_service.format_news_data(news_data)
        
        # Store the fresh news in Supabase
        await store_news(formatted_news, category="top")
        return formatted_news
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching top news: {str(e)}")


@app.get("/topic-headlines/{topic}", response_model=List[Dict[str, Any]])
async def get_topic_headlines(
    topic: str,
    use_cache: bool = Query(True, description="Use cached news if available")
):
    """
    Get headlines for a specific topic
    
    Valid topics: business, technology, entertainment, sports, health, science, world
    """
    # Only include topics supported by PyGoogleNews topic_headlines
    valid_topics = ["business", "technology", "entertainment", 
                   "sports", "health", "science", "world"]
    
    if topic.lower() not in valid_topics:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid topic. Choose from: {', '.join(valid_topics)}"
        )
    
    try:
        if use_cache:
            # Try to get cached news first
            cached_news = await get_stored_news(category=topic.lower())
            if cached_news:
                return cached_news

        # Fetch fresh news if cache is disabled or empty
        news_data = news_service.get_topic_headlines(topic)
        formatted_news = news_service.format_news_data(news_data)
        
        # Store the fresh news in Supabase
        await store_news(formatted_news, category=topic.lower())
        return formatted_news
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


@app.get("/supabase/stats")
async def get_supabase_stats():
    """Get Supabase database statistics"""
    try:
        stats = await get_categories_stats()
        return {
            "categories": stats,
            "total_categories": len(stats),
            "database": "Supabase"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching Supabase stats: {str(e)}"
        )


@app.get("/search-db", response_model=List[Dict[str, Any]])
async def search_database(
    query: str = Query(..., description="Search query"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(20, description="Maximum number of results")
):
    """Advanced search in cached articles with full-text search"""
    try:
        results = await search_news_in_db(query, category, limit)
        return results
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error searching database: {str(e)}"
        )


@app.get("/trending", response_model=List[Dict[str, Any]])
async def get_trending_news(
    hours: int = Query(24, description="Hours to look back for trending articles"),
    limit: int = Query(10, description="Maximum number of articles")
):
    """Get trending articles from the last N hours"""
    try:
        articles = await get_trending_articles(hours, limit)
        return articles
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching trending articles: {str(e)}"
        )


@app.get("/sources/{source_name}", response_model=List[Dict[str, Any]])
async def get_news_by_source(
    source_name: str,
    limit: int = Query(20, description="Maximum number of articles")
):
    """Get articles from a specific news source"""
    try:
        articles = await get_articles_by_source(source_name, limit)
        return articles
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching articles from source '{source_name}': {str(e)}"
        )


@app.get("/popular-sources", response_model=List[Dict[str, Any]])
async def get_top_sources(
    limit: int = Query(10, description="Maximum number of sources")
):
    """Get most popular news sources by article count"""
    try:
        sources = await get_popular_sources(limit)
        return sources
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching popular sources: {str(e)}"
        )


@app.post("/cleanup")
async def cleanup_database(
    days_old: int = Query(30, description="Delete articles older than this many days"),
    confirm: bool = Query(False, description="Confirm deletion")
):
    """Clean up old articles from the database"""
    if not confirm:
        return {
            "message": "Add ?confirm=true to actually delete articles",
            "preview": f"Would delete articles older than {days_old} days"
        }
    
    try:
        result = await cleanup_old_articles(days_old)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error cleaning up database: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """Comprehensive health check endpoint"""
    try:
        # Test database connection
        stats = await get_categories_stats()
        
        # Test news service
        news_data = news_service.get_top_news()
        
        return {
            "status": "healthy",
            "database": "connected",
            "categories": len(stats),
            "news_service": "operational",
            "timestamp": "2024-01-01T00:00:00Z"  # Would be actual timestamp
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": "2024-01-01T00:00:00Z"
        } 