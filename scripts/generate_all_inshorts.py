#!/usr/bin/env python3
"""
Script to process all news categories and generate Inshorts-style summaries.
This script uses the Selenium-based approach to extract images and content from all news categories.
"""

import os
import glob
import argparse
import logging
import sys
import subprocess
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Generate Inshorts-style summaries for all news categories")
    
    parser.add_argument(
        "--input-dir", 
        default="data",
        help="Directory containing news JSON files"
    )
    
    parser.add_argument(
        "--output-dir", 
        default="data/inshorts",
        help="Directory to save Inshorts-style summaries"
    )
    
    parser.add_argument(
        "--max-articles", 
        type=int,
        default=20,
        help="Maximum number of articles to process per category"
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
    
    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Run browser in headless mode"
    )
    
    parser.add_argument(
        "--categories",
        nargs="+",
        help="Specific categories to process (default: all available)"
    )
    
    return parser.parse_args()

def get_available_categories(input_dir):
    """Get available news categories from input directory"""
    categories = []
    for file_path in glob.glob(os.path.join(input_dir, 'news_*.json')):
        # Extract category from filename (news_category.json)
        category = os.path.basename(file_path).replace('news_', '').replace('.json', '')
        categories.append(category)
    return categories

def process_category(category, input_dir, output_dir, max_articles, timeout, summary_length, headless):
    """Process a single news category"""
    input_file = os.path.join(input_dir, f'news_{category}.json')
    output_file = os.path.join(output_dir, f'inshorts_{category}.json')
    
    # Skip if input file doesn't exist
    if not os.path.exists(input_file):
        logger.warning(f"Input file not found: {input_file}")
        return False
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Build command
    cmd = [
        sys.executable,
        'scripts/generate_inshorts_selenium.py',
        '--input', input_file,
        '--output', output_file,
        '--max-articles', str(max_articles),
        '--timeout', str(timeout),
        '--summary-length', str(summary_length)
    ]
    
    if headless:
        cmd.append('--headless')
    
    # Run the command
    logger.info(f"Processing category: {category}")
    logger.info(f"Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logger.info(f"Successfully processed category: {category}")
        logger.debug(result.stdout.decode())
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error processing category {category}: {e}")
        logger.error(e.stderr.decode())
        return False

def main():
    """Main function"""
    args = parse_args()
    
    try:
        # Get available categories
        if args.categories:
            categories = args.categories
        else:
            categories = get_available_categories(args.input_dir)
        
        if not categories:
            logger.error(f"No news categories found in {args.input_dir}")
            return 1
        
        logger.info(f"Found {len(categories)} news categories: {', '.join(categories)}")
        
        # Process each category
        success_count = 0
        for category in categories:
            if process_category(
                category,
                args.input_dir,
                args.output_dir,
                args.max_articles,
                args.timeout,
                args.summary_length,
                args.headless
            ):
                success_count += 1
        
        logger.info(f"Processed {success_count}/{len(categories)} categories successfully")
        
        if success_count == len(categories):
            return 0
        else:
            return 1
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main()) 