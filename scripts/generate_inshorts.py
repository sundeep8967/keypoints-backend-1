#!/usr/bin/env python3
"""
Script to generate Inshorts-style news summaries.
"""

import os
import json
import argparse
import logging
from datetime import datetime
import sys
from pathlib import Path

# Add the parent directory to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from app.news_service import NewsService
from app.summarizer import NewsSummarizer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
    
    return parser.parse_args()

def load_news_data(input_path):
    """Load news data from JSON file"""
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading news data: {e}")
        return None

def save_to_json(data, output_path):
    """Save data to a JSON file"""
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    # Save data to JSON file
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Inshorts-style news data saved to {output_path}")
    logger.info(f"Processed {len(data['articles'])} articles")

def generate_inshorts_summaries(news_data, max_length=60, max_articles=10):
    """Generate Inshorts-style summaries for news articles"""
    if not news_data or 'articles' not in news_data:
        logger.error("Invalid news data format")
        return None
    
    articles = news_data.get('articles', [])[:max_articles]
    inshorts_articles = []
    
    for article in articles:
        try:
            # Get the article URL
            url = article.get('link')
            if not url:
                continue
                
            # Generate a summary
            summary = NewsSummarizer.summarize_from_url(url)
            if not summary:
                continue
                
            # Format in Inshorts style
            inshorts_summary = NewsSummarizer.format_inshorts_style(
                article.get('title', ''), 
                summary, 
                max_chars=max_length
            )
            
            # Create Inshorts-style article
            inshorts_article = {
                'title': article.get('title'),
                'link': url,
                'short_summary': inshorts_summary,
                'source': article.get('source'),
                'published': article.get('published'),
                'image_url': article.get('image_url')  # This might not be available in your data
            }
            
            inshorts_articles.append(inshorts_article)
            logger.info(f"Generated Inshorts-style summary for: {article.get('title')}")
            
        except Exception as e:
            logger.error(f"Error processing article: {e}")
    
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
        # Load news data
        news_data = load_news_data(args.input)
        if not news_data:
            return 1
            
        # Generate Inshorts-style summaries
        inshorts_data = generate_inshorts_summaries(
            news_data, 
            max_length=args.max_length,
            max_articles=args.max_articles
        )
        
        if not inshorts_data:
            return 1
            
        # Save to JSON file
        save_to_json(inshorts_data, args.output)
        
        return 0
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 