#!/usr/bin/env python3
"""
Script to push all generated inshorts-style news data to Supabase.
This script reads all inshorts_*.json files and uploads them to Supabase.
"""

import os
import json
import glob
import asyncio
import logging
import sys
from pathlib import Path
from typing import Dict, List
from datetime import datetime

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.db import store_news, map_source_to_final_category

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_inshorts_file(file_path: str) -> Dict:
    """Load inshorts data from a JSON file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Loaded {len(data.get('articles', []))} articles from {file_path}")
        return data
    except Exception as e:
        logger.error(f"Error loading {file_path}: {e}")
        return {}

def convert_inshorts_to_supabase_format(inshorts_data: Dict, category: str) -> List[Dict]:
    """Convert inshorts format to Supabase format with validation"""
    articles = []
    skipped_count = 0
    
    if 'articles' not in inshorts_data:
        return articles
    
    for article in inshorts_data['articles']:
        title = article.get("title", "").strip()
        summary = article.get("summary", "").strip()
        image_url = article.get("image_url", "").strip() if article.get("image_url") else ""
        
        # Validation: Skip articles with missing essential fields
        if not title:
            logger.warning(f"   ⚠️  Skipping article: Missing title")
            skipped_count += 1
            continue
            
            
        if not image_url or image_url == "https://via.placeholder.com/300x150?text=No+Image":
            logger.warning(f"   ⚠️  Skipping article: Missing or placeholder image - {title[:50]}...")
            skipped_count += 1
            continue
        
        # Use description field (which contains the rich article content)
        description_content = article.get("description", "").strip()
        
        # Convert inshorts format to Supabase format - only push description field
        supabase_article = {
            "title": title,
            "link": article.get("url", ""),  # inshorts uses 'url', supabase expects 'link'
            "published": article.get("published", ""),
            "source": article.get("source", ""),
            "category": category,
            "description": description_content if description_content else None,  # Only description field
            "image_url": image_url,
            "article_id": article.get("id"),  # Store the inshorts ID
            "quality_score": article.get("quality_score", 0)
        }
        articles.append(supabase_article)
    
    if skipped_count > 0:
        logger.info(f"   📋 Validation: Skipped {skipped_count} articles with missing essential fields")
    
    return articles

def get_category_from_filename(filename: str) -> str:
    """Extract category name from inshorts filename"""
    # Remove 'inshorts_' prefix and '.json' suffix
    category = filename.replace('inshorts_', '').replace('.json', '')
    return category




async def push_all_inshorts_to_supabase(data_dir: str = "data") -> Dict:
    """Push all inshorts files to Supabase"""
    
    logger.info("🚀 Starting Inshorts to Supabase upload process")
    logger.info("=" * 60)
    
    # Find all inshorts files
    inshorts_pattern = os.path.join(data_dir, "inshorts_*.json")
    inshorts_files = glob.glob(inshorts_pattern)
    
    if not inshorts_files:
        logger.warning(f"No inshorts files found in {data_dir}")
        return {
            "success": False,
            "error": "No inshorts files found",
            "total_articles": 0,
            "categories_processed": 0
        }
    
    logger.info(f"Found {len(inshorts_files)} inshorts files:")
    for file_path in inshorts_files:
        logger.info(f"  • {os.path.basename(file_path)}")
    
    total_articles_uploaded = 0
    categories_processed = 0
    upload_results = {}
    
    # Process each inshorts file
    for file_path in inshorts_files:
        # Extract the filename from the full path
        filename = os.path.basename(file_path)
        # Get the original source category from the filename
        source_category = get_category_from_filename(filename)
        
        # Map to the final, clean category for Supabase
        final_category = map_source_to_final_category(source_category)
        
        logger.info(f"\n📰 Processing source category: {source_category} -> Mapped to: {final_category}")
        logger.info(f"   File: {filename}")
        
        # Load the inshorts data
        inshorts_data = load_inshorts_file(file_path)
        
        if not inshorts_data or 'articles' not in inshorts_data:
            logger.warning(f"   ⚠️  No articles found in {filename}")
            continue
        
        # Convert to Supabase format
        supabase_articles = convert_inshorts_to_supabase_format(inshorts_data, final_category)
        
        if not supabase_articles:
            logger.warning(f"   ⚠️  No valid articles to upload for {source_category} (all articles failed validation)")
            continue
        
        logger.info(f"   📝 Validated and converted {len(supabase_articles)} high-quality articles for upload")
        
        # Show sample article info
        if supabase_articles:
            sample = supabase_articles[0]
            logger.info(f"   📋 Sample: {sample.get('title', 'No title')[:50]}...")
            image_url = sample.get('image_url') or 'No image'
            logger.info(f"   🖼️  Image: {str(image_url)[:50]}...")
        
        # Upload to Supabase
        logger.info(f"   💾 Uploading to Supabase...")
        result = await store_news(supabase_articles, category=final_category)
        
        upload_results[source_category] = result
        
        if result["success"]:
            articles_count = result.get("stored_count", 0)
            total_articles_uploaded += articles_count
            categories_processed += 1
            logger.info(f"   ✅ SUCCESS! Uploaded {articles_count} articles for {source_category}")
        else:
            error_msg = result.get("error", "Unknown error")
            logger.error(f"   ❌ FAILED! Error uploading {source_category}: {error_msg}")
    
    # Final summary
    logger.info("\n" + "=" * 60)
    logger.info("🎉 UPLOAD COMPLETE!")
    logger.info(f"📊 Summary:")
    logger.info(f"   • Total categories processed: {categories_processed}/{len(inshorts_files)}")
    logger.info(f"   • Total articles uploaded: {total_articles_uploaded}")
    logger.info(f"   • Upload timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Show per-category results
    logger.info(f"\n📋 Per-category results:")
    for category, result in upload_results.items():
        status = "✅" if result["success"] else "❌"
        count = result.get("stored_count", 0)
        logger.info(f"   {status} {category}: {count} articles")
    
    logger.info(f"\n🎯 Check your Supabase dashboard:")
    logger.info(f"   1. Go to https://app.supabase.com")
    logger.info(f"   2. Open your project")
    logger.info(f"   3. Table Editor → news_articles")
    logger.info(f"   4. You should see {total_articles_uploaded} new articles!")
    
    return {
        "success": categories_processed > 0,
        "total_articles": total_articles_uploaded,
        "categories_processed": categories_processed,
        "categories_total": len(inshorts_files),
        "upload_results": upload_results
    }

async def main():
    """Main function"""
    try:
        # Check if data directory exists
        data_dir = "data"
        if not os.path.exists(data_dir):
            logger.error(f"Data directory '{data_dir}' not found!")
            return 1
        
        # Push all inshorts data to Supabase
        result = await push_all_inshorts_to_supabase(data_dir)
        
        if result["success"]:
            logger.info(f"\n🎉 All done! Successfully uploaded {result['total_articles']} articles across {result['categories_processed']} categories.")
            return 0
        else:
            logger.error(f"\n❌ Upload failed or no articles uploaded.")
            return 1
            
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)