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
import time
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
    
    parser.add_argument(
        "--use-shared-browser",
        action="store_true",
        default=True,
        help="Use shared browser instance across categories for better performance (default: True)"
    )
    
    parser.add_argument(
        "--legacy-mode",
        action="store_true",
        default=False,
        help="Use legacy mode with separate browser instances per category"
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

def setup_shared_browser(headless=True):
    """Set up a shared Selenium WebDriver for reuse across categories"""
    try:
        # Add the parent directory to sys.path to import selenium setup
        sys.path.append(str(Path(__file__).parent))
        
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
            logger.info("Setting up shared browser in headless mode")
        
        # Initialize Chrome WebDriver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(30)
        logger.info("Shared browser instance created successfully")
        return driver
    except Exception as e:
        logger.error(f"Error setting up shared browser: {e}")
        raise

def process_category_with_shared_browser(category, input_dir, output_dir, max_articles, timeout, summary_length, driver):
    """Process a single news category using a shared browser instance"""
    input_file = os.path.join(input_dir, f'news_{category}.json')
    output_file = os.path.join(output_dir, f'inshorts_{category}.json')
    
    # Skip if input file doesn't exist
    if not os.path.exists(input_file):
        logger.warning(f"Input file not found: {input_file}")
        return False
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    logger.info(f"Processing category: {category}")
    
    try:
        # Import the processing functions directly
        sys.path.append(str(Path(__file__).parent))
        from generate_inshorts_selenium import load_news_data, process_news_data, save_to_json
        import time
        
        # Load news data
        news_data = load_news_data(input_file)
        
        # Process news data to generate summaries using shared browser
        processed_articles = process_news_data(
            news_data, 
            max_articles, 
            driver,
            timeout,
            summary_length
        )
        
        # Prepare output data
        output_data = {
            'metadata': {
                'source_file': input_file,
                'generation_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                'total_articles': len(processed_articles)
            },
            'articles': processed_articles
        }
        
        # Save to JSON file
        save_to_json(output_data, output_file)
        
        logger.info(f"Successfully processed category: {category}")
        return True
    except Exception as e:
        logger.error(f"Error processing category {category}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def process_category(category, input_dir, output_dir, max_articles, timeout, summary_length, headless):
    """Process a single news category (legacy method - kept for compatibility)"""
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
        
        # Choose processing mode based on arguments
        if args.legacy_mode:
            logger.info("Using legacy mode with separate browser instances per category")
            # Process each category using legacy method
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
        else:
            logger.info("Using shared browser mode for better performance")
            # Set up shared browser instance
            logger.info("Setting up shared browser instance for all categories...")
            driver = setup_shared_browser(headless=args.headless)
            
            try:
                # Process each category using the shared browser
                success_count = 0
                for category in categories:
                    if process_category_with_shared_browser(
                        category,
                        args.input_dir,
                        args.output_dir,
                        args.max_articles,
                        args.timeout,
                        args.summary_length,
                        driver
                    ):
                        success_count += 1
            finally:
                # Always clean up the browser instance
                logger.info("Cleaning up shared browser instance...")
                driver.quit()
        
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