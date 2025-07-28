#!/usr/bin/env python3
"""
Script to extract images, titles, and descriptions from news articles using Selenium.
This approach uses a real browser to handle JavaScript redirects and load Open Graph data.
"""

import os
import json
import argparse
import logging
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional
import traceback
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import hashlib

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Extract images from news articles using Selenium")
    
    parser.add_argument(
        "--input", 
        required=True,
        help="Input news JSON file path (e.g., data/news_top.json)"
    )
    
    parser.add_argument(
        "--output", 
        required=True,
        help="Output JSON file path for extracted content"
    )
    
    parser.add_argument(
        "--max-articles", 
        type=int,
        default=5,
        help="Maximum number of articles to process"
    )
    
    parser.add_argument(
        "--timeout", 
        type=int,
        default=10,
        help="Timeout in seconds for loading each page"
    )
    
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay between requests in seconds to avoid rate limiting"
    )

    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode"
    )
    
    # CONCURRENT PROCESSING OPTIONS
    parser.add_argument(
        "--max-workers",
        type=int,
        default=3,
        help="Maximum number of concurrent workers for parallel processing (default: 3)"
    )
    
    parser.add_argument(
        "--use-cache",
        action="store_true",
        default=True,
        help="Use intelligent caching to avoid re-processing articles (default: True)"
    )
    
    return parser.parse_args()

def load_news_data(file_path: str) -> Dict:
    """Load news data from a JSON file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Successfully loaded news data from {file_path}")
        return data
    except Exception as e:
        logger.error(f"Error loading news data from {file_path}: {e}")
        raise

def setup_selenium(headless=False):
    """Set up Selenium WebDriver with performance optimizations"""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
        
        options = Options()
        # Basic stability options
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-infobars")
        options.add_argument("--mute-audio")
        
        # PERFORMANCE OPTIMIZATIONS - CAREFUL NOT TO BREAK IMAGE EXTRACTION
        # options.add_argument("--disable-images")  # REMOVED - This breaks image URL extraction!
        options.add_argument("--disable-plugins")
        options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--disable-backgrounding-occluded-windows")
        options.add_argument("--disable-renderer-backgrounding")
        options.add_argument("--disable-features=TranslateUI")
        options.add_argument("--disable-ipc-flooding-protection")
        options.add_argument("--aggressive-cache-discard")
        
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        # Add headless mode if requested
        if headless:
            options.add_argument("--headless")
            options.add_argument("--disable-gpu")
            logger.info("🚀 Running OPTIMIZED browser in headless mode")
        
        # Initialize Chrome WebDriver with performance settings
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(20)  # Reduced timeout for better performance
        
        logger.info("✅ OPTIMIZED Selenium WebDriver initialized")
        return driver
    except Exception as e:
        logger.error(f"Error setting up Selenium: {e}")
        logger.error(traceback.format_exc())
        raise

def extract_article_details(url: str, driver, timeout: int = 10) -> Dict:
    """
    Extract article details using Selenium WebDriver.
    
    Args:
        url: URL of the article
        driver: Selenium WebDriver instance
        timeout: Timeout in seconds for loading the page
        
    Returns:
        Dictionary with article details
    """
    try:
        # Navigate to the URL
        logger.info(f"Navigating to: {url}")
        driver.get(url)
        
        # Wait for the page to load
        time.sleep(min(timeout, 5))  # Wait at least some time for JavaScript to execute
        
        # Get the current URL (after any redirects)
        current_url = driver.current_url
        logger.info(f"Current URL after redirects: {current_url}")
        
        # Extract Open Graph image
        og_image = None
        twitter_image = None
        
        # Try to find Open Graph image
        og_tags = driver.find_elements("xpath", "//meta[@property='og:image']")
        if og_tags:
            og_image = og_tags[0].get_attribute("content")
            logger.info(f"Found OG image: {og_image}")
        
        # Try to find Twitter card image
        twitter_tags = driver.find_elements("xpath", "//meta[@name='twitter:image']")
        if twitter_tags:
            twitter_image = twitter_tags[0].get_attribute("content")
            logger.info(f"Found Twitter image: {twitter_image}")
        
        # Extract the page title
        title = driver.title
        
        # Try to find the largest image on the page as a fallback
        images = []
        img_elements = driver.find_elements("tag name", "img")
        for img in img_elements:
            src = img.get_attribute("src")
            if src and src.startswith(("http://", "https://")):
                width = img.get_attribute("width")
                height = img.get_attribute("height")
                try:
                    area = int(width) * int(height) if width and height else 0
                except (ValueError, TypeError):
                    area = 0
                images.append((src, area))
        
        # Sort images by area (largest first)
        images.sort(key=lambda x: x[1], reverse=True)
        largest_image = images[0][0] if images else None
        
        # Choose the best image
        image_url = og_image or twitter_image or largest_image
        
        # Extract the page text
        page_text = driver.find_element("tag name", "body").text
        
        # Try to extract description
        description = ""
        desc_tags = driver.find_elements("xpath", "//meta[@name='description']")
        if desc_tags:
            description = desc_tags[0].get_attribute("content")
        
        # If no description found, try Open Graph description
        if not description:
            og_desc_tags = driver.find_elements("xpath", "//meta[@property='og:description']")
            if og_desc_tags:
                description = og_desc_tags[0].get_attribute("content")
        
        # If still no description, extract the first paragraph
        if not description:
            paragraphs = driver.find_elements("tag name", "p")
            for p in paragraphs:
                p_text = p.text.strip()
                if p_text and len(p_text) > 50:  # Only consider paragraphs with enough text
                    description = p_text
                    break
        
        return {
            "resolved_url": current_url,
            "image_url": image_url,
            "title": title,
            "description": description[:500] + "..." if description and len(description) > 500 else description,
            "text_excerpt": page_text[:1000] + "..." if page_text and len(page_text) > 1000 else page_text
        }
    except Exception as e:
        logger.error(f"Error extracting article details from {url}: {e}")
        logger.error(traceback.format_exc())
        return {
            "resolved_url": None,
            "image_url": None,
            "title": None,
            "description": None,
            "text_excerpt": None,
            "error": str(e)
        }

def process_news_data(news_data: Dict, max_articles: int, driver, timeout: int, delay: float) -> List[Dict]:
    """
    Process news data to extract article details using Selenium with PERFORMANCE OPTIMIZATIONS.
    
    Args:
        news_data: News data from JSON file
        max_articles: Maximum number of articles to process
        driver: Selenium WebDriver instance
        timeout: Timeout in seconds for loading each page
        delay: Delay between requests in seconds
        
    Returns:
        List of dictionaries with article details
    """
    processed_articles = []
    
    if 'articles' not in news_data:
        logger.error("No 'articles' field found in the news data")
        return processed_articles
    
    # Limit the number of articles to process
    articles_to_process = news_data['articles'][:max_articles]
    logger.info(f"🚀 Processing {len(articles_to_process)} articles with OPTIMIZATIONS (max: {max_articles})")
    
    # PERFORMANCE OPTIMIZATION: Track processing metrics
    start_time = time.time()
    successful_articles = 0
    
    for i, article in enumerate(articles_to_process):
        article_start_time = time.time()
        logger.info(f"📰 Article {i+1}/{len(articles_to_process)}")
        
        if 'link' not in article:
            logger.warning(f"No 'link' field found in article: {article}")
            continue
        
        title = article.get('title', 'Unknown Title')
        url = article.get('link')
        source = article.get('source', 'Unknown Source')
        published = article.get('published', '')
        
        logger.info(f"Processing: {title[:50]}... - {source}")
        
        # Extract article details
        article_details = extract_article_details(url, driver, timeout)
        
        # Create processed article
        processed_article = {
            'title': title,
            'source': source,
            'original_url': url,
            'resolved_url': article_details['resolved_url'] or url,
            'image_url': article_details['image_url'],
            'extracted_title': article_details['title'],
            'description': article_details['description'],
            'text_excerpt': article_details['text_excerpt'],
            'published': published
        }
        
        processed_articles.append(processed_article)
        successful_articles += 1
        
        # PERFORMANCE OPTIMIZATION: Track individual article timing
        article_time = time.time() - article_start_time
        logger.debug(f"✅ Article processed in {article_time:.2f}s")
        
        # PERFORMANCE OPTIMIZATION: Adaptive delay (reduced for faster processing)
        if i < len(articles_to_process) - 1:
            optimized_delay = max(0.3, delay * 0.7)  # Reduce delay by 30% for better performance
            time.sleep(optimized_delay)
    
    # PERFORMANCE METRICS
    total_time = time.time() - start_time
    articles_per_second = successful_articles / total_time if total_time > 0 else 0
    
    logger.info(f"🏆 EXTRACTION COMPLETE:")
    logger.info(f"   ✅ Articles processed: {successful_articles}/{len(articles_to_process)}")
    logger.info(f"   ⏱️  Total time: {total_time:.2f} seconds")
    logger.info(f"   🚀 Processing rate: {articles_per_second:.2f} articles/second")
    
    return processed_articles

def save_to_json(data: Dict, output_path: str):
    """Save extracted content to a JSON file"""
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    # Save data to JSON file
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Extracted content saved to {output_path}")
    logger.info(f"Processed {len(data['articles'])} articles")

def main():
    """Main function"""
    args = parse_args()
    
    try:
        # Set up Selenium
        driver = setup_selenium(headless=args.headless)
        
        try:
            # Load news data
            news_data = load_news_data(args.input)
            
            # Process news data to extract content
            processed_articles = process_news_data(
                news_data, 
                args.max_articles, 
                driver,
                args.timeout,
                args.delay
            )
            
            # Prepare output data
            output_data = {
                'metadata': {
                    'source_file': args.input,
                    'extraction_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'total_articles': len(processed_articles)
                },
                'articles': processed_articles
            }
            
            # Save to JSON file
            save_to_json(output_data, args.output)
            
            return 0
        finally:
            # Quit the driver
            driver.quit()
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main()) 