#!/usr/bin/env python3
"""
Main orchestrator script for the complete news processing workflow.

This script executes the full 3-step process:
1. Fetch news from various sources
2. Extract images and generate summaries using Selenium
3. Push processed data to Supabase

Usage:
    python main.py                          # Run full workflow with default settings
    python main.py --categories tech sports # Run only specific categories
    python main.py --max-articles 10        # Process more articles per category
    python main.py --skip-supabase          # Skip Supabase upload step
"""

import os
import sys
import argparse
import logging
import subprocess
import time
from pathlib import Path
from typing import List, Optional
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Default news categories to process
DEFAULT_CATEGORIES = [
    "top",
    "business", 
    "technology",
    "entertainment",
    "sports",
    "health",
    "science",
    "world",
    "trending",
    "politics", 
    "national", 
    "india", 
    "automobile", 
    "startups",
    "travel", 
    "fashion", 
    "education", 
    "miscellaneous",
    "scandal",
    "viral", 
    "crime",
    "celebrity",
    "political_scandal"
]

# Extended categories including scandal and viral content

# Categories supported by PyGoogleNews topic_headlines
SUPPORTED_TOPIC_CATEGORIES = [
    "business", 
    "technology",
    "entertainment",
    "sports",
    "health",
    "science",
    "world"
]

# Categories that need to be fetched via search instead of topic
SEARCH_BASED_CATEGORIES = {
    "trending": "trending news",
    "politics": "politics news",
    "national": "national news",
    "india": "India news",
    "automobile": "automobile automotive car news",
    "startups": "startup business news",
    "travel": "travel tourism news",
    "fashion": "fashion style news",
    "education": "education school university news",
    "miscellaneous": "general news",
    # New scandal and viral categories
    "scandal": "scandal controversy corruption exposed",
    "viral": "viral trending goes viral internet sensation",
    "crime": "arrest investigation fraud lawsuit criminal charges",
    "celebrity": "celebrity scandal hollywood controversy celebrity drama",
    "political_scandal": "political scandal government corruption election fraud"
}

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Complete news processing workflow: Fetch → Extract → Upload",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                                    # Full workflow, all categories
  python main.py --categories tech sports          # Only tech and sports
  python main.py --max-articles 10 --headless     # More articles, headless mode
  python main.py --skip-fetch                     # Skip fetch, only process existing
  python main.py --skip-supabase                  # Skip Supabase upload
        """
    )
    
    # Categories to process
    # Combine all available categories for command line choices
    ALL_AVAILABLE_CATEGORIES = DEFAULT_CATEGORIES + list(SEARCH_BASED_CATEGORIES.keys())
    
    parser.add_argument(
        "--categories",
        nargs="+",
        choices=ALL_AVAILABLE_CATEGORIES,
        default=DEFAULT_CATEGORIES,
        help=f"Categories to process (default: all categories). Available: {', '.join(ALL_AVAILABLE_CATEGORIES)}"
    )
    
    # Processing options
    parser.add_argument(
        "--max-articles",
        type=int,
        default=5,
        help="Maximum articles to process per category (default: 5)"
    )
    
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Timeout in seconds for each article extraction (default: 10)"
    )
    
    parser.add_argument(
        "--summary-length",
        type=int,
        default=60,
        help="Maximum summary length in words (default: 60)"
    )
    
    # Browser options
    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Run browser in headless mode (default: True)"
    )
    
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Run browser with GUI (overrides --headless)"
    )
    
    # Step control options
    parser.add_argument(
        "--skip-fetch",
        action="store_true",
        help="Skip news fetching step (use existing news files)"
    )
    
    parser.add_argument(
        "--skip-extract",
        action="store_true", 
        help="Skip image extraction and summarization step"
    )
    
    parser.add_argument(
        "--skip-supabase",
        action="store_true",
        help="Skip Supabase upload step"
    )
    
    # Data directories
    parser.add_argument(
        "--data-dir",
        default="data",
        help="Directory for news data files (default: data)"
    )
    
    # News service options
    parser.add_argument(
        "--language",
        default="en",
        help="Language code for news (default: en)"
    )
    
    parser.add_argument(
        "--country",
        default="US", 
        help="Country code for news (default: US)"
    )
    
    return parser.parse_args()

def run_command(cmd: List[str], description: str) -> bool:
    """Run a command and return success status"""
    logger.info(f"🔄 {description}")
    logger.debug(f"Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd, 
            check=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True
        )
        logger.info(f"✅ {description} - SUCCESS")
        if result.stdout.strip():
            logger.debug(f"Output: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ {description} - FAILED")
        logger.error(f"Error: {e}")
        if e.stderr:
            logger.error(f"Stderr: {e.stderr}")
        return False

def step1_fetch_news(categories: List[str], data_dir: str, language: str, country: str) -> int:
    """Step 1: Fetch news for all categories"""
    logger.info("\n" + "="*60)
    logger.info("📰 STEP 1: FETCHING NEWS")
    logger.info("="*60)
    
    success_count = 0
    
    for category in categories:
        output_file = os.path.join(data_dir, f"news_{category}.json")
        
        if category == "top":
            cmd = [
                sys.executable, "scripts/fetch_news.py",
                "--type", "top",
                "--output", output_file,
                "--language", language,
                "--country", country
            ]
        elif category in SUPPORTED_TOPIC_CATEGORIES:
            cmd = [
                sys.executable, "scripts/fetch_news.py", 
                "--type", "topic",
                "--topic", category,
                "--output", output_file,
                "--language", language,
                "--country", country
            ]
        elif category in SEARCH_BASED_CATEGORIES:
            # Use search for unsupported topics
            search_query = SEARCH_BASED_CATEGORIES[category]
            cmd = [
                sys.executable, "scripts/fetch_news.py",
                "--type", "search",
                "--query", search_query,
                "--when", "1d",  # Last 1 day
                "--output", output_file,
                "--language", language,
                "--country", country
            ]
        else:
            logger.warning(f"⚠️  Unknown category: {category}, skipping...")
            continue
        
        if run_command(cmd, f"Fetching {category} news"):
            success_count += 1
        
        # Small delay between requests to be respectful
        time.sleep(1)
    
    logger.info(f"\n📊 Step 1 Summary: {success_count}/{len(categories)} categories fetched successfully")
    return success_count

def step2_extract_and_summarize(categories: List[str], data_dir: str, max_articles: int, 
                               timeout: int, summary_length: int, headless: bool) -> int:
    """Step 2: Extract images and generate summaries"""
    logger.info("\n" + "="*60)
    logger.info("🖼️ STEP 2: EXTRACTING IMAGES & GENERATING SUMMARIES")
    logger.info("="*60)
    
    success_count = 0
    
    for category in categories:
        input_file = os.path.join(data_dir, f"news_{category}.json")
        output_file = os.path.join(data_dir, f"inshorts_{category}.json")
        
        # Check if input file exists
        if not os.path.exists(input_file):
            logger.warning(f"⚠️  Input file not found: {input_file}")
            continue
        
        cmd = [
            sys.executable, "scripts/generate_inshorts_selenium.py",
            "--input", input_file,
            "--output", output_file,
            "--max-articles", str(max_articles),
            "--timeout", str(timeout),
            "--summary-length", str(summary_length)
        ]
        
        if headless:
            cmd.append("--headless")
        
        if run_command(cmd, f"Processing {category} articles"):
            success_count += 1
    
    logger.info(f"\n📊 Step 2 Summary: {success_count}/{len(categories)} categories processed successfully")
    return success_count

def step3_upload_to_supabase(data_dir: str) -> bool:
    """Step 3: Upload processed data to Supabase"""
    logger.info("\n" + "="*60)
    logger.info("🚀 STEP 3: UPLOADING TO SUPABASE")
    logger.info("="*60)
    
    cmd = [sys.executable, "scripts/push_inshorts_to_supabase.py"]
    
    return run_command(cmd, "Uploading all processed data to Supabase")

def check_prerequisites():
    """Check if all required files and dependencies exist"""
    logger.info("🔍 Checking prerequisites...")
    
    required_scripts = [
        "scripts/fetch_news.py",
        "scripts/generate_inshorts_selenium.py", 
        "scripts/push_inshorts_to_supabase.py"
    ]
    
    missing_files = []
    for script in required_scripts:
        if not os.path.exists(script):
            missing_files.append(script)
    
    if missing_files:
        logger.error(f"❌ Missing required scripts: {', '.join(missing_files)}")
        return False
    
    # Check if data directory exists, create if not
    if not os.path.exists("data"):
        logger.info("📁 Creating data directory...")
        os.makedirs("data", exist_ok=True)
    
    logger.info("✅ Prerequisites check passed")
    return True

def print_summary(args, step1_success: int, step2_success: int, step3_success: bool):
    """Print final summary of the workflow"""
    logger.info("\n" + "="*60)
    logger.info("📋 WORKFLOW SUMMARY")
    logger.info("="*60)
    
    total_categories = len(args.categories)
    
    if not args.skip_fetch:
        logger.info(f"📰 Step 1 (Fetch): {step1_success}/{total_categories} categories")
    else:
        logger.info("📰 Step 1 (Fetch): SKIPPED")
    
    if not args.skip_extract:
        logger.info(f"🖼️  Step 2 (Extract): {step2_success}/{total_categories} categories")
    else:
        logger.info("🖼️  Step 2 (Extract): SKIPPED")
    
    if not args.skip_supabase:
        status = "SUCCESS" if step3_success else "FAILED"
        logger.info(f"🚀 Step 3 (Upload): {status}")
    else:
        logger.info("🚀 Step 3 (Upload): SKIPPED")
    
    logger.info(f"\n📊 Categories processed: {', '.join(args.categories)}")
    logger.info(f"📈 Max articles per category: {args.max_articles}")
    
    # Check for generated files
    inshorts_files = []
    for category in args.categories:
        inshorts_file = os.path.join(args.data_dir, f"inshorts_{category}.json")
        if os.path.exists(inshorts_file):
            try:
                with open(inshorts_file, 'r') as f:
                    data = json.load(f)
                    article_count = len(data.get('articles', []))
                    inshorts_files.append(f"{category}: {article_count} articles")
            except:
                inshorts_files.append(f"{category}: file exists")
    
    if inshorts_files:
        logger.info(f"\n📄 Generated files:")
        for file_info in inshorts_files:
            logger.info(f"   • {file_info}")

def main():
    """Main function to orchestrate the complete workflow"""
    args = parse_args()
    
    # Handle headless override
    if args.no_headless:
        args.headless = False
    
    
    logger.info("🚀 Starting Complete News Processing Workflow")
    logger.info(f"📂 Data directory: {args.data_dir}")
    logger.info(f"📰 Categories: {', '.join(args.categories)}")
    logger.info(f"📊 Max articles per category: {args.max_articles}")
    logger.info(f"🖥️  Browser mode: {'Headless' if args.headless else 'GUI'}")
    
    # Check prerequisites
    if not check_prerequisites():
        logger.error("❌ Prerequisites check failed. Exiting.")
        return 1
    
    start_time = time.time()
    step1_success = 0
    step2_success = 0
    step3_success = False
    
    try:
        # Step 1: Fetch News
        if not args.skip_fetch:
            step1_success = step1_fetch_news(
                args.categories, 
                args.data_dir, 
                args.language, 
                args.country
            )
            if step1_success == 0:
                logger.error("❌ No news was fetched successfully. Stopping workflow.")
                return 1
        else:
            logger.info("⏭️  Skipping Step 1: News fetching")
        
        # Step 2: Extract Images and Generate Summaries
        if not args.skip_extract:
            step2_success = step2_extract_and_summarize(
                args.categories,
                args.data_dir,
                args.max_articles,
                args.timeout,
                args.summary_length,
                args.headless
            )
            if step2_success == 0:
                logger.error("❌ No articles were processed successfully. Stopping workflow.")
                return 1
        else:
            logger.info("⏭️  Skipping Step 2: Image extraction and summarization")
        
        # Step 3: Upload to Supabase
        if not args.skip_supabase:
            step3_success = step3_upload_to_supabase(args.data_dir)
        else:
            logger.info("⏭️  Skipping Step 3: Supabase upload")
            step3_success = True  # Consider it successful if skipped
        
        # Print summary
        end_time = time.time()
        duration = end_time - start_time
        
        print_summary(args, step1_success, step2_success, step3_success)
        
        logger.info(f"\n⏱️  Total execution time: {duration:.1f} seconds")
        
        # Determine exit code
        if args.skip_supabase:
            # If Supabase is skipped, success depends on extraction step
            if args.skip_extract or step2_success > 0:
                logger.info("🎉 Workflow completed successfully!")
                return 0
            else:
                logger.error("❌ Workflow failed!")
                return 1
        else:
            # If Supabase is not skipped, all steps must succeed
            if step3_success and (args.skip_extract or step2_success > 0):
                logger.info("🎉 Workflow completed successfully!")
                return 0
            else:
                logger.error("❌ Workflow failed!")
                return 1
                
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Workflow interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"\n❌ Unexpected error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main())