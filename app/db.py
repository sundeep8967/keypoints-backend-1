import os
from supabase import create_client, Client
from dotenv import load_dotenv
from typing import List, Dict, Optional
import logging

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Initialize Supabase client
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

if not supabase_url:
    raise ValueError("SUPABASE_URL must be set in environment variables")

if not supabase_key:
    logger.warning("SUPABASE_KEY not found, using URL-based connection")
    # For direct PostgreSQL connection, we'll use a different approach
    supabase = None
else:
    supabase: Client = create_client(supabase_url, supabase_key)

# Database operations
async def store_news(news_data: List[Dict], category: str = "general") -> Dict:
    """Store news articles in Supabase"""
    try:
        if not supabase:
            logger.error("Supabase client not initialized")
            return {"success": False, "error": "Supabase not configured"}
            
        # Prepare data for insertion
        articles_to_insert = []
        for article in news_data:
            # Use description field (which contains the rich article content)
            description_content = article.get("description", "")
            
            article_data = {
                "title": article.get("title", ""),
                "link": article.get("link", ""),
                "published": article.get("published", ""),
                "source": article.get("source", ""),
                "category": category,
                "description": description_content if description_content else None,  # Only description field
                "image_url": article.get("image_url"),
                "article_id": article.get("article_id"),
                "quality_score": article.get("quality_score", 0)
            }
            articles_to_insert.append(article_data)
        
        # Insert into Supabase
        response = supabase.table("news_articles").insert(articles_to_insert).execute()
        
        logger.info(f"Successfully stored {len(articles_to_insert)} articles in category '{category}'")
        return {
            "success": True,
            "stored_count": len(articles_to_insert),
            "data": response.data
        }
        
    except Exception as e:
        logger.error(f"Error storing news in Supabase: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "stored_count": 0
        }

async def get_stored_news(category: Optional[str] = None, limit: int = 50) -> List[Dict]:
    """Retrieve news articles from Supabase"""
    try:
        if not supabase:
            logger.error("Supabase client not initialized")
            return []
            
        # Build query
        query = supabase.table("news_articles").select("*")
        
        if category:
            query = query.eq("category", category)
        
        # Order by created_at descending and limit results
        query = query.order("created_at", desc=True).limit(limit)
        
        response = query.execute()
        
        logger.info(f"Retrieved {len(response.data)} articles" + 
                   (f" for category '{category}'" if category else ""))
        
        return response.data
        
    except Exception as e:
        logger.error(f"Error retrieving news from Supabase: {str(e)}")
        return []

async def search_news_in_db(query: str, category: Optional[str] = None, limit: int = 20) -> List[Dict]:
    """Advanced search for news articles in Supabase with full-text search"""
    try:
        if not supabase:
            logger.error("Supabase client not initialized")
            return []
            
        # Use the custom search function we created in the schema
        search_query = f"""
        SELECT * FROM search_articles('{query}', {f"'{category}'" if category else 'NULL'})
        LIMIT {limit}
        """
        
        response = supabase.rpc('search_articles', {
            'search_query': query,
            'category_filter': category
        }).limit(limit).execute()
        
        logger.info(f"Found {len(response.data)} articles matching '{query}'")
        return response.data
        
    except Exception as e:
        # Fallback to simple search
        logger.warning(f"Advanced search failed, using fallback: {str(e)}")
        try:
            db_query = supabase.table("news_articles").select("*")
            
            # Simple text matching
            db_query = db_query.ilike("title", f"%{query}%")
            
            if category:
                db_query = db_query.eq("category", category)
            
            db_query = db_query.order("created_at", desc=True).limit(limit)
            response = db_query.execute()
            
            return response.data
        except Exception as fallback_error:
            logger.error(f"Fallback search also failed: {str(fallback_error)}")
            return []

async def get_trending_articles(hours: int = 24, limit: int = 10) -> List[Dict]:
    """Get trending articles based on recent activity"""
    try:
        if not supabase:
            return []
            
        # Get articles from the last N hours
        response = supabase.table("news_articles").select("*").gte(
            "created_at", 
            f"now() - interval '{hours} hours'"
        ).order("created_at", desc=True).limit(limit).execute()
        
        logger.info(f"Found {len(response.data)} trending articles from last {hours} hours")
        return response.data
        
    except Exception as e:
        logger.error(f"Error getting trending articles: {str(e)}")
        return []

async def get_articles_by_source(source: str, limit: int = 20) -> List[Dict]:
    """Get articles from a specific news source"""
    try:
        if not supabase:
            return []
            
        response = supabase.table("news_articles").select("*").eq(
            "source", source
        ).order("created_at", desc=True).limit(limit).execute()
        
        logger.info(f"Found {len(response.data)} articles from source '{source}'")
        return response.data
        
    except Exception as e:
        logger.error(f"Error getting articles by source: {str(e)}")
        return []

async def get_popular_sources(limit: int = 10) -> List[Dict]:
    """Get most popular news sources by article count"""
    try:
        if not supabase:
            return []
            
        # This would need a custom query or aggregation
        response = supabase.table("news_articles").select(
            "source", count="exact"
        ).execute()
        
        # Group by source (simplified - in production use proper aggregation)
        source_counts = {}
        for article in response.data:
            source = article.get("source", "Unknown")
            source_counts[source] = source_counts.get(source, 0) + 1
        
        # Sort by count and return top sources
        popular_sources = [
            {"source": source, "article_count": count}
            for source, count in sorted(source_counts.items(), key=lambda x: x[1], reverse=True)
        ][:limit]
        
        return popular_sources
        
    except Exception as e:
        logger.error(f"Error getting popular sources: {str(e)}")
        return []

async def bulk_update_articles(updates: List[Dict]) -> Dict:
    """Bulk update multiple articles"""
    try:
        if not supabase:
            return {"success": False, "error": "Supabase not configured"}
            
        updated_count = 0
        errors = []
        
        for update in updates:
            try:
                article_id = update.pop("id")
                response = supabase.table("news_articles").update(update).eq("id", article_id).execute()
                updated_count += 1
            except Exception as e:
                errors.append(f"Failed to update article {article_id}: {str(e)}")
        
        return {
            "success": True,
            "updated_count": updated_count,
            "errors": errors
        }
        
    except Exception as e:
        logger.error(f"Error in bulk update: {str(e)}")
        return {"success": False, "error": str(e)}

async def get_categories_stats() -> Dict:
    """Get statistics for all news categories"""
    try:
        if not supabase:
            return {}
            
        # Get count by category
        response = supabase.table("news_articles").select("category", count="exact").execute()
        
        # This is a simplified version - you might want to use a proper aggregation query
        stats = {}
        for item in response.data:
            category = item.get("category", "unknown")
            stats[category] = stats.get(category, 0) + 1
            
        return stats
        
    except Exception as e:
        logger.error(f"Error getting category stats: {str(e)}")
        return {}

async def cleanup_old_articles(days_old: int = 30) -> Dict:
    """Delete articles older than specified days"""
    try:
        if not supabase:
            return {"success": False, "error": "Supabase not configured"}
            
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days_old)
        cutoff_str = cutoff_date.isoformat()
        
        # Delete old articles
        response = supabase.table("news_articles").delete().lt("created_at", cutoff_str).execute()
        
        deleted_count = len(response.data) if response.data else 0
        
        logger.info(f"Deleted {deleted_count} old articles")
        
        return {
            "success": True,
            "deleted_count": deleted_count
        }
        
    except Exception as e:
        logger.error(f"Error deleting old articles: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "deleted_count": 0
        }

def map_source_to_final_category(source_category: str) -> str:
    """Map a complex source category to a single, final category for Supabase"""
    
    source_lower = source_category.lower().strip()
    
    # Indian cities/states that should map to "india" (except Bengaluru)
    indian_cities_states = [
        "mumbai", "delhi", "chennai", "hyderabad", "pune", "kolkata",
        "maharashtra", "tamil nadu", "telangana", "west bengal", "ncr",
        "new delhi", "gurgaon", "noida", "ahmedabad", "surat", "jaipur",
        "lucknow", "kanpur", "nagpur", "indore", "thane", "bhopal",
        "visakhapatnam", "pimpri", "patna", "vadodara", "ludhiana",
        "agra", "nashik", "faridabad", "meerut", "rajkot", "kalyan",
        "vasai", "varanasi", "srinagar", "aurangabad", "dhanbad",
        "amritsar", "navi mumbai", "allahabad", "ranchi", "howrah",
        "coimbatore", "jabalpur", "gwalior", "vijayawada", "jodhpur",
        "madurai", "raipur", "kota", "guwahati", "chandigarh"
    ]
    
    # Check if it's Bengaluru (keep separate)
    if "bengaluru" in source_lower or "bangalore" in source_lower:
        return "bengaluru"
    
    # Check if it's any other Indian city/state (map to "india")
    for city_state in indian_cities_states:
        if city_state in source_lower:
            return "india"
    
    # Specific mappings for other categories
    specific_mappings = {
        "indian cinema and bollywood": "entertainment",
        "indian celebrity": "entertainment", 
        "indian sports": "sports",
        "indian politics": "politics",
        "indian education": "education",
        "indian scandal and crime": "crime",
        "trending in bengaluru and india": "trending",
        "international": "world",
        "india": "india"  # General India news stays as "india"
    }
    
    # Check for exact matches first
    if source_lower in specific_mappings:
        return specific_mappings[source_lower]
    
    # Priority list of base categories for partial matching
    # This order is important - more specific categories should come first
    priority_list = [
        "trending", "politics", "education", "sports", "entertainment", 
        "celebrity", "cinema", "crime", "scandal", "technology", 
        "world", "business", "health", "science"
    ]
    
    # Check for keywords from the priority list in the source category
    for base_category in priority_list:
        if base_category.lower() in source_lower:
            return base_category
    
    # If it contains "indian" or "india" but no specific category, map to "india"
    if "indian" in source_lower or "india" in source_lower:
        return "india"
            
    # Fallback: if no match is found, use the original source category
    # This is a safe default, but we should aim to have all categories mapped.
    logger.warning(f"No mapping found for '{source_category}'. Using original name.")
    return source_category