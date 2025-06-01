#!/usr/bin/env python3
"""
Script to generate Inshorts-style news summaries.
"""

import os
import json
import argparse
import logging
import time
from datetime import datetime
import sys
from pathlib import Path
import traceback

# Add the parent directory to sys.path
sys.path.append(str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import dependencies with error handling
try:
    from app.news_service import NewsService
    from app.summarizer import NewsSummarizer
    import nltk
    import newspaper
    logger.info(f"Successfully imported dependencies: NLTK {nltk.__version__}, newspaper3k {newspaper.__version__}")
except ImportError as e:
    logger.error(f"Failed to import required dependencies: {e}")
    logger.error(traceback.format_exc())
    sys.exit(1)

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Generate Inshorts-style news summaries")
    
    # Input options
    parser.add_argument(
        "--input", 
        required=True,
        help="Input JSON file with news data"
    )
    
    # Output options
    parser.add_argument(
        "--output", 
        default="inshorts_news.json",
        help="Output file path (default: inshorts_news.json)"
    )
    
    # Summary options
    parser.add_argument(
        "--max-length",
        type=int,
        default=60,
        help="Maximum length of each sentence in the summary"
    )
    
    parser.add_argument(
        "--max-articles",
        type=int,
        default=10,
        help="Maximum number of articles to process"
    )
    
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Timeout in seconds for processing each article"
    )
    
    return parser.parse_args()

def load_news_data(input_path):
    """Load news data from JSON file"""
    try:
        logger.info(f"Loading news data from {input_path}")
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Successfully loaded news data with {len(data.get('articles', []))} articles")
        return data
    except Exception as e:
        logger.error(f"Error loading news data from {input_path}: {e}")
        logger.error(traceback.format_exc())
        return None

def save_to_json(data, output_path):
    """Save data to a JSON file"""
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    try:
        # Save data to JSON file
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Inshorts-style news data saved to {output_path}")
        logger.info(f"Processed {len(data['articles'])} articles")
    except Exception as e:
        logger.error(f"Error saving data to {output_path}: {e}")
        logger.error(traceback.format_exc())

def process_article_with_timeout(article, max_length, timeout):
    """Process a single article with timeout"""
    url = article.get('link')
    if not url:
        logger.warning("Skipping article with no URL")
        return None
    
    logger.info(f"Processing article: {article.get('title', 'Untitled')} | URL: {url}")
    
    try:
        # Set a timeout for article processing
        start_time = time.time()
        
        # Get enhanced article data with images
        article_data = NewsSummarizer.summarize_from_url(url, timeout=timeout)
        if not article_data or not article_data.get('summary'):
            logger.warning(f"No summary generated for {url}")
            return None
            
        # Check timeout
        if time.time() - start_time > timeout:
            logger.warning(f"Timeout processing article: {url}")
            return None
            
        # Format in Inshorts style
        inshorts_summary = NewsSummarizer.format_inshorts_style(
            article.get('title', '') or article_data.get('title', ''), 
            article_data.get('summary', ''), 
            max_chars=max_length
        )
        
        # Create enhanced Inshorts-style article
        inshorts_article = {
            'title': article.get('title') or article_data.get('title', 'Untitled'),
            'link': url,
            'short_summary': inshorts_summary,
            'full_summary': article_data.get('summary', ''),
            'source': article.get('source'),
            'published': article.get('published'),
            'image_url': article_data.get('top_image'),
            'additional_images': article_data.get('images', [])[:3],
            'authors': article_data.get('authors', []),
            'text_excerpt': article_data.get('text', '')
        }
        
        logger.info(f"Successfully generated enhanced summary for: {inshorts_article['title']}")
        return inshorts_article
        
    except Exception as e:
        logger.error(f"Error processing article {url}: {e}")
        logger.error(traceback.format_exc())
        return None

def generate_inshorts_summaries(news_data, max_length=60, max_articles=10, timeout=30):
    """Generate Inshorts-style summaries for news articles"""
    if not news_data or 'articles' not in news_data:
        logger.error("Invalid news data format")
        return None
    
    articles = news_data.get('articles', [])[:max_articles]
    logger.info(f"Processing {len(articles)} articles (max: {max_articles})")
    
    inshorts_articles = []
    
    for i, article in enumerate(articles):
        try:
            logger.info(f"Article {i+1}/{len(articles)}")
            inshorts_article = process_article_with_timeout(article, max_length, timeout)
            if inshorts_article:
                inshorts_articles.append(inshorts_article)
        except Exception as e:
            logger.error(f"Unexpected error processing article: {e}")
            logger.error(traceback.format_exc())
    
    # Create result with metadata
    result = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "source": news_data.get('metadata', {}).get('info', 'Unknown'),
            "count": len(inshorts_articles)
        },
        "articles": inshorts_articles
    }
    
    return result

def main():
    """Main function"""
    args = parse_args()
    
    try:
        logger.info(f"Starting Inshorts generation with args: {args}")
        
        # Load news data
        news_data = load_news_data(args.input)
        if not news_data:
            logger.error("Failed to load news data, exiting")
            return 1
            
        # Generate Inshorts-style summaries
        inshorts_data = generate_inshorts_summaries(
            news_data, 
            max_length=args.max_length,
            max_articles=args.max_articles,
            timeout=args.timeout
        )
        
        if not inshorts_data:
            logger.error("Failed to generate Inshorts summaries, exiting")
            return 1
            
        # Save to JSON file
        save_to_json(inshorts_data, args.output)
        
        logger.info("Inshorts generation completed successfully")
        return 0
    except Exception as e:
        logger.error(f"Unhandled error: {str(e)}")
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main()) 