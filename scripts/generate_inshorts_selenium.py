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

def setup_selenium(headless=True):
    """Set up Selenium WebDriver"""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
        
        options = Options()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-infobars")
        options.add_argument("--mute-audio")
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        # Add headless mode if requested
        if headless:
            options.add_argument("--headless")
            options.add_argument("--disable-gpu")
            logger.info("Running in headless mode")
        
        # Initialize Chrome WebDriver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(30)
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

def process_news_data(news_data: Dict, max_articles: int, driver, timeout: int, summary_length: int) -> List[Dict]:
    """
    Process news data to generate Inshorts-style summaries.
    
    Args:
        news_data: News data from JSON file
        max_articles: Maximum number of articles to process
        driver: Selenium WebDriver instance
        timeout: Timeout in seconds for each article
        summary_length: Maximum length of summary in words
        
    Returns:
        List of dictionaries with Inshorts-style summaries
    """
    processed_articles = []
    
    if 'articles' not in news_data:
        logger.error("No 'articles' field found in the news data")
        return processed_articles
    
    # Limit the number of articles to process
    articles_to_process = news_data['articles'][:max_articles]
    logger.info(f"Processing {len(articles_to_process)} articles (max: {max_articles})")
    
    for i, article in enumerate(articles_to_process):
        logger.info(f"Article {i+1}/{len(articles_to_process)}")
        
        if 'link' not in article:
            logger.warning(f"No 'link' field found in article: {article}")
            continue
        
        title = article.get('title', 'Unknown Title')
        url = article.get('link')
        source = article.get('source', 'Unknown Source')
        published = article.get('published', '')
        
        logger.info(f"Processing article: {title} - {source} | URL: {url}")
        
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
        
        processed_articles.append(processed_article)
        
        # Add delay between requests
        if i < len(articles_to_process) - 1:
            time.sleep(1)
    
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
            
            # Process news data to generate summaries
            processed_articles = process_news_data(
                news_data, 
                args.max_articles, 
                driver,
                args.timeout,
                args.summary_length
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