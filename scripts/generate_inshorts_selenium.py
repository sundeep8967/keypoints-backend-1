#!/usr/bin/env python3
"""
Script to generate Inshorts-style news summaries from news data.
Uses the Selenium-based approach to handle Google News redirects and extract images.
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
import hashlib  # For generating article IDs
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Generate Inshorts-style news summaries")
    
    parser.add_argument(
        "--input", 
        required=True,
        help="Input news JSON file path (e.g., data/news_top.json)"
    )
    
    parser.add_argument(
        "--output", 
        required=True,
        help="Output JSON file path for Inshorts-style summaries"
    )
    
    parser.add_argument(
        "--max-articles", 
        type=int,
        default=10,
        help="Maximum number of articles to process"
    )
    
    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Run browser in headless mode"
    )
    
    parser.add_argument(
        "--timeout", 
        type=int,
        default=10,
        help="Timeout in seconds for each article"
    )
    
    parser.add_argument(
        "--summary-length",
        type=int,
        default=60,
        help="Maximum length of summary in words"
    )
    
    # CONCURRENT PROCESSING OPTIONS
    parser.add_argument(
        "--max-workers",
        type=int,
        default=1,
        help="Maximum number of concurrent workers for parallel processing (default: 1 - disabled to avoid issues)"
    )
    
    return parser.parse_args()

# Removed problematic caching system that created too many files

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

def setup_selenium(headless=True):
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

def _is_valid_article_url(url: str) -> bool:
    """Check if URL is a valid article URL (not social media, ads, etc.)"""
    if not url or not url.startswith(('http://', 'https://')):
        return False
    
    # Exclude common non-article domains
    excluded_domains = [
        'google.com', 'youtube.com', 'facebook.com', 'twitter.com', 'instagram.com',
        'linkedin.com', 'pinterest.com', 'reddit.com', 'tiktok.com',
        'ads.', 'doubleclick.', 'googleadservices.', 'googlesyndication.',
        'amazon.com/dp/', 'amazon.com/gp/', 'ebay.com'
    ]
    
    url_lower = url.lower()
    for domain in excluded_domains:
        if domain in url_lower:
            return False
    
    # Must contain common news indicators
    news_indicators = [
        '/article/', '/news/', '/story/', '/post/', '/blog/', 
        '.html', '.htm', '/20', '/article-', '/news-'
    ]
    
    # If it has news indicators, it's likely valid
    for indicator in news_indicators:
        if indicator in url_lower:
            return True
    
    # If it's from a known news domain, it's probably valid
    news_domains = [
        'cnn.com', 'bbc.com', 'reuters.com', 'ap.org', 'npr.org',
        'nytimes.com', 'washingtonpost.com', 'wsj.com', 'bloomberg.com',
        'guardian.com', 'independent.co.uk', 'telegraph.co.uk',
        'timesofindia.com', 'hindustantimes.com', 'indianexpress.com',
        'ndtv.com', 'news18.com', 'zeenews.com', 'deccanherald.com'
    ]
    
    for domain in news_domains:
        if domain in url_lower:
            return True
    
    # Default: if it's not obviously bad, allow it
    return len(url) > 20 and '/' in url[10:]

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
        
        # HANDLE GOOGLE NEWS REDIRECTS - Improved with multiple strategies
        if "news.google.com" in current_url:
            logger.info("🔄 Detected Google News page, attempting to click through to actual article...")
            try:
                # Strategy 1: Wait for dynamic content to load
                time.sleep(2)
                
                # Strategy 2: Try multiple selectors in order of preference
                selectors_to_try = [
                    # Most specific selectors first
                    "article a[href*='http']:not([href*='google.com']):not([href*='youtube.com'])",
                    "a[data-n-tid]:not([href*='google.com'])",
                    "[role='article'] a[href*='http']:not([href*='google.com'])",
                    "h3 a[href*='http']:not([href*='google.com'])",
                    "h4 a[href*='http']:not([href*='google.com'])",
                    # More general selectors
                    "a[href*='http']:not([href*='google.com']):not([href*='youtube.com']):not([href*='facebook.com'])",
                    # Last resort - any external link
                    "a[href^='http']:not([href*='google'])"
                ]
                
                article_links = []
                for selector in selectors_to_try:
                    try:
                        article_links = driver.find_elements("css selector", selector)
                        if article_links:
                            logger.info(f"✅ Found {len(article_links)} links using selector: {selector}")
                            break
                    except Exception as e:
                        logger.debug(f"Selector failed: {selector} - {e}")
                        continue
                
                # Strategy 3: Filter and validate links
                valid_links = []
                for link in article_links[:10]:  # Check first 10 links only
                    try:
                        href = link.get_attribute('href')
                        if href and _is_valid_article_url(href):
                            valid_links.append((link, href))
                    except:
                        continue
                
                if valid_links:
                    # Get the best article link (first valid one)
                    best_link, actual_url = valid_links[0]
                    logger.info(f"🔗 Found valid article link: {actual_url}")
                    
                    # Strategy 4: Try clicking first, fallback to direct navigation
                    try:
                        # Try clicking the link
                        driver.execute_script("arguments[0].click();", best_link)
                        time.sleep(3)
                        
                        # Check if we were redirected
                        new_url = driver.current_url
                        if "news.google.com" not in new_url:
                            current_url = new_url
                            logger.info(f"✅ Click redirect successful: {current_url}")
                        else:
                            # Fallback: direct navigation
                            logger.info("🔄 Click failed, trying direct navigation...")
                            driver.get(actual_url)
                            time.sleep(3)
                            current_url = driver.current_url
                            logger.info(f"✅ Direct navigation successful: {current_url}")
                    
                    except Exception as e:
                        logger.warning(f"Click failed, trying direct navigation: {e}")
                        # Fallback: direct navigation
                        driver.get(actual_url)
                        time.sleep(3)
                        current_url = driver.current_url
                        logger.info(f"✅ Direct navigation successful: {current_url}")
                
                else:
                    logger.warning("❌ No valid article links found on Google News page")
                    
            except Exception as e:
                logger.warning(f"❌ Error handling Google News redirect: {e}")
                # Continue with Google News page if redirect fails
        
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
            "title": title or None,
            "description": description[:500] + "..." if description and len(description) > 500 else description,
            "text_excerpt": page_text[:1000] + "..." if page_text and len(page_text) > 1000 else page_text
        }
    except Exception as e:
        logger.error(f"Error extracting article details from {url}: {e}")
        logger.error(traceback.format_exc())
        return {
            "resolved_url": None,
            "image_url": "https://via.placeholder.com/300x150?text=No+Image",
            "title": None,
            "description": None,
            "text_excerpt": None,
            "error": str(e)
        }

def generate_summary(text: str, max_words: int = 60) -> str:
    """
    Generate a summary of the text with a maximum number of words.
    
    Args:
        text: Text to summarize
        max_words: Maximum number of words in the summary
        
    Returns:
        Summary text
    """
    try:
        # Clean up the text - remove navigation, menus, etc.
        lines = text.split('\n')
        
        # Remove very short lines (likely navigation/menu items)
        filtered_lines = []
        for line in lines:
            line = line.strip()
            if len(line) > 30 and not line.startswith('Skip to') and not line.isupper():
                filtered_lines.append(line)
        
        # Join the filtered lines
        cleaned_text = ' '.join(filtered_lines)
        
        # Simple sentence splitting based on common sentence endings
        def split_into_sentences(text):
            # Split by common sentence endings
            sentences = []
            current = ""
            for char in text:
                current += char
                # Check for sentence endings (., !, ?)
                if char in ['.', '!', '?'] and len(current.strip()) > 10:
                    sentences.append(current.strip())
                    current = ""
            
            # Add any remaining text as a sentence
            if current.strip():
                sentences.append(current.strip())
                
            return sentences
        
        # Split the text into sentences
        sentences = split_into_sentences(cleaned_text)
        
        # Get the first few sentences up to max_words
        summary = ""
        word_count = 0
        
        for sentence in sentences:
            words = sentence.split()
            if word_count + len(words) <= max_words:
                summary += sentence + " "
                word_count += len(words)
            else:
                # Add as many words as possible from the sentence
                remaining_words = max_words - word_count
                if remaining_words > 0:
                    partial_sentence = " ".join(words[:remaining_words]) + "..."
                    summary += partial_sentence
                break
        
        # If no sentences were found or summary is empty, use a simple word-based approach
        if not summary:
            # Simple summary - just take first 60 words
            if not cleaned_text:
                return "No content available for summarization."
                
            words = cleaned_text.split()
            if len(words) <= max_words:
                return cleaned_text
            else:
                return " ".join(words[:max_words]) + "..."
                
        return summary.strip()
    except Exception as e:
        logger.error(f"Error generating summary: {e}")
        return text[:200] + "..." if text and len(text) > 200 else text or "No content available for summarization."

def process_single_article(article: Dict, driver, timeout: int, summary_length: int) -> Dict:
    """Process a single article (simplified without problematic caching)"""
    try:
        title = article.get('title', 'Unknown Title')
        url = article.get('link')
        source = article.get('source', 'Unknown Source')
        published = article.get('published', '')
        
        if not url:
            return {
                'id': 'no-url',
                'title': title,
                'source': source,
                'url': '',
                'image_url': 'https://via.placeholder.com/300x150?text=No+URL',
                'summary': 'No URL provided for this article.',
                'published': published,
                'error': 'No URL provided'
            }
        
        logger.debug(f"🔄 Processing: {title[:50]}... - {source}")
        
        # Extract article details using Selenium
        article_details = extract_article_details(url, driver, timeout)
        
        # Generate summary
        if article_details['text_excerpt']:
            summary = generate_summary(article_details['text_excerpt'], summary_length)
        elif article_details['description']:
            summary = generate_summary(article_details['description'], summary_length)
        else:
            summary = "No content available for summarization."
        
        # Generate a unique ID for the article
        article_id = generate_article_id(url, title, source)
        
        # Create Inshorts-style article
        processed_article = {
            'id': article_id,
            'title': title,
            'source': source,
            'url': article_details['resolved_url'] or url,
            'image_url': article_details['image_url'],
            'summary': summary,
            'published': published
        }
        
        return processed_article
        
    except Exception as e:
        logger.error(f"Error processing article {title[:50]}...: {e}")
        return {
            'id': 'error',
            'title': title,
            'source': source,
            'url': url or '',
            'image_url': 'https://via.placeholder.com/300x150?text=Error',
            'summary': f'Error processing article: {str(e)}',
            'published': published,
            'error': str(e)
        }

def process_news_data(news_data: Dict, max_articles: int, driver, timeout: int, summary_length: int, 
                     max_workers: int = 3, use_cache: bool = False) -> List[Dict]:
    """
    Process news data with CONCURRENT PROCESSING (simplified without problematic caching).
    
    Args:
        news_data: News data from JSON file
        max_articles: Maximum number of articles to process
        driver: Selenium WebDriver instance
        timeout: Timeout in seconds for each article
        summary_length: Maximum length of summary in words
        max_workers: Maximum number of concurrent workers
        use_cache: Disabled to avoid file creation issues
        
    Returns:
        List of dictionaries with Inshorts-style summaries
    """
    processed_articles = []
    
    if 'articles' not in news_data:
        logger.error("No 'articles' field found in the news data")
        return processed_articles
    
    # Limit the number of articles to process
    articles_to_process = news_data['articles'][:max_articles]
    logger.info(f"🚀 Processing {len(articles_to_process)} articles with CONCURRENT PROCESSING (workers: {max_workers})")
    
    # PERFORMANCE OPTIMIZATION: Track processing metrics
    start_time = time.time()
    successful_articles = 0
    
    if max_workers == 1:
        # Sequential processing (fallback)
        logger.info("🔄 Using sequential processing")
        for i, article in enumerate(articles_to_process):
            result = process_single_article(article, driver, timeout, summary_length)
            processed_articles.append(result)
            if 'error' not in result:
                successful_articles += 1
    else:
        # CONCURRENT PROCESSING - Process multiple articles simultaneously
        logger.info(f"⚡ Using CONCURRENT processing with {max_workers} workers")
        
        # Create multiple driver instances for concurrent processing
        drivers = [driver]  # Use the main driver
        try:
            # Create additional drivers for concurrent processing
            for i in range(max_workers - 1):
                additional_driver = setup_selenium(headless=True)
                drivers.append(additional_driver)
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all articles for processing
                future_to_article = {}
                for i, article in enumerate(articles_to_process):
                    # Distribute articles across available drivers
                    driver_to_use = drivers[i % len(drivers)]
                    future = executor.submit(process_single_article, article, driver_to_use, timeout, summary_length)
                    future_to_article[future] = article
                
                # Collect results as they complete
                for future in as_completed(future_to_article):
                    article = future_to_article[future]
                    try:
                        result = future.result()
                        processed_articles.append(result)
                        if 'error' not in result:
                            successful_articles += 1
                            
                    except Exception as e:
                        logger.error(f"Error in concurrent processing: {e}")
                        # Add error result
                        processed_articles.append({
                            'id': 'error',
                            'title': article.get('title', 'Unknown'),
                            'source': article.get('source', 'Unknown'),
                            'url': article.get('link', ''),
                            'image_url': 'https://via.placeholder.com/300x150?text=Error',
                            'summary': f'Concurrent processing error: {str(e)}',
                            'published': article.get('published', ''),
                            'error': str(e)
                        })
        
        finally:
            # Clean up additional drivers
            for i in range(1, len(drivers)):
                try:
                    drivers[i].quit()
                except:
                    pass
    
    # PERFORMANCE METRICS
    total_time = time.time() - start_time
    articles_per_second = successful_articles / total_time if total_time > 0 else 0
    
    logger.info(f"🏆 CONCURRENT PROCESSING COMPLETE:")
    logger.info(f"   ✅ Articles processed: {successful_articles}/{len(articles_to_process)}")
    logger.info(f"   ⏱️  Total time: {total_time:.2f} seconds")
    logger.info(f"   🚀 Processing rate: {articles_per_second:.2f} articles/second")
    logger.info(f"   ⚡ Speedup from concurrency: ~{max_workers}x potential")
    
    return processed_articles

def generate_article_id(url: str, title: str, source: str) -> str:
    """
    Generate a unique ID for an article based on its URL, title and source.
    
    Args:
        url: Article URL
        title: Article title
        source: Article source
        
    Returns:
        Unique article ID
    """
    # Create a string combining key article attributes
    combined = f"{url}|{title}|{source}"
    
    # Generate a hash of the combined string
    hash_obj = hashlib.md5(combined.encode())
    
    # Return the hexadecimal digest
    return hash_obj.hexdigest()

def save_to_json(data: Dict, output_path: str):
    """Save Inshorts-style summaries to a JSON file"""
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    # Save data to JSON file
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Inshorts-style summaries saved to {output_path}")
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
            
            # Process news data to generate summaries with CONCURRENT PROCESSING
            processed_articles = process_news_data(
                news_data, 
                args.max_articles, 
                driver,
                args.timeout,
                args.summary_length,
                args.max_workers,
                args.use_cache
            )
            
            # Prepare output data
            output_data = {
                'metadata': {
                    'source_file': args.input,
                    'generation_time': time.strftime('%Y-%m-%d %H:%M:%S'),
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