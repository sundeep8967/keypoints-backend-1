#!/usr/bin/env python3
"""
Main orchestrator script using Playwright for web automation and content extraction.

This script executes the full 3-step process:
1. Fetch news from various sources
2. Extract images and generate summaries using Playwright
3. Push processed data to Supabase

Usage:
    python main.py                          # Run full workflow with Playwright
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
import asyncio

from app.db import map_source_to_final_category

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import same categories and configurations as main.py
DEFAULT_CATEGORIES = [
    "Bengaluru",
    "technology",
    "indian celebrity",
    "entertainment ",
    "indian sports",
    "international",
    "trending in bengaluru and india",
    "indian politics", 
    "india",
    "indian education",
    "indian scandal and crime",
    "indian cinema and bollywood",
    "mumbai",
    "delhi",
    "chennai",
    "hyderabad",
    "pune",
    "kolkata"
]

SUPPORTED_TOPIC_CATEGORIES = [
    "business", 
    "technology",
    "entertainment",
    "sports",
    "health",
    "science",
    "world"
]

CUSTOM_SEARCH_QUERIES = {
    "trending": "trending news",
    "politics": "politics news",
    "india": "India news",
    "education": "education school university news",
    "miscellaneous": "general news",
    "scandal": "scandal controversy corruption exposed",
    "viral": "viral trending goes viral internet sensation",
    "crime": "arrest investigation fraud lawsuit criminal charges",
    "celebrity": "celebrity scandal hollywood controversy celebrity drama",
    "political_scandal": "political scandal government corruption election fraud",
    "mumbai": "Mumbai news Maharashtra",
    "delhi": "Delhi news NCR New Delhi",
    "chennai": "Chennai news Tamil Nadu",
    "hyderabad": "Hyderabad news Telangana",
    "pune": "Pune news Maharashtra",
    "kolkata": "Kolkata news West Bengal"
}

SEARCH_BASED_CATEGORIES = {}
for category in DEFAULT_CATEGORIES:
    if category not in SUPPORTED_TOPIC_CATEGORIES and category != "top":
        SEARCH_BASED_CATEGORIES[category] = CUSTOM_SEARCH_QUERIES.get(category, f"{category} news")

def parse_args():
    """Parse command line arguments (same as main.py but with Playwright note)"""
    parser = argparse.ArgumentParser(
        description="Complete news processing workflow using Playwright: Fetch → Extract → Upload",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main_playwright.py                                    # Full workflow, all categories (Playwright)
  python main_playwright.py --categories tech sports          # Only tech and sports (Playwright)
  python main_playwright.py --max-articles 10 --headless     # More articles, headless mode (Playwright)
  python main_playwright.py --skip-fetch                     # Skip fetch, only process existing (Playwright)
  python main_playwright.py --skip-supabase                  # Skip Supabase upload (Playwright)
        """
    )
    
    ALL_AVAILABLE_CATEGORIES = DEFAULT_CATEGORIES + list(SEARCH_BASED_CATEGORIES.keys())
    
    parser.add_argument(
        "--categories",
        nargs="+",
        choices=ALL_AVAILABLE_CATEGORIES,
        default=DEFAULT_CATEGORIES,
        help=f"Categories to process (default: all categories). Available: {', '.join(ALL_AVAILABLE_CATEGORIES)}"
    )
    
    parser.add_argument(
        "--max-articles",
        type=int,
        default=20,
        help="Maximum articles to process per category (default: 20)"
    )
    
    parser.add_argument(
        "--timeout",
        type=int,
        default=8,
        help="Timeout in seconds for each article extraction (default: 8, optimized)"
    )
    
    parser.add_argument(
        "--summary-length",
        type=int,
        default=60,
        help="Maximum summary length in words (default: 60)"
    )
    
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
    
    parser.add_argument(
        "--data-dir",
        default="data",
        help="Directory for news data files (default: data)"
    )
    
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
    """Run a command and return success status (same as main.py)"""
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

# Import all the same helper functions from main.py
def fetch_single_category_to_temp(args_tuple):
    """Fetch news for a single category to a temporary file (same as main.py)"""
    category, temp_output, data_dir, language, country = args_tuple
    
    if category == "top":
        cmd = [
            sys.executable, "app/news_service.py",
            "--type", "top",
            "--output", temp_output,
            "--language", language,
            "--country", country
        ]
    elif category in SUPPORTED_TOPIC_CATEGORIES:
        cmd = [
            sys.executable, "app/news_service.py", 
            "--type", "topic",
            "--topic", category,
            "--output", temp_output,
            "--language", language,
            "--country", country
        ]
    elif category in SEARCH_BASED_CATEGORIES:
        search_query = SEARCH_BASED_CATEGORIES[category]
        cmd = [
            sys.executable, "app/news_service.py",
            "--type", "search",
            "--query", search_query,
            "--when", "1d",
            "--output", temp_output,
            "--language", language,
            "--country", country
        ]
    else:
        logger.warning(f"⚠️  Unknown category: {category}, skipping...")
        return False
    
    return run_command(cmd, f"Fetching {category} news")

def merge_news_files(temp_files: List[str], final_output: str, final_category: str) -> bool:
    """Merge multiple news files into a single final file (same as main.py)"""
    try:
        merged_articles = []
        merged_metadata = {
            "type": "merged",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "final_category": final_category,
            "source_files": [],
            "count": 0
        }
        
        for temp_file in temp_files:
            if not os.path.exists(temp_file):
                logger.warning(f"⚠️  Temp file not found: {temp_file}")
                continue
                
            try:
                with open(temp_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                if 'articles' in data:
                    merged_articles.extend(data['articles'])
                    merged_metadata["source_files"].append({
                        "file": os.path.basename(temp_file),
                        "original_info": data.get('metadata', {}),
                        "article_count": len(data['articles'])
                    })
                    
            except Exception as e:
                logger.error(f"❌ Error reading temp file {temp_file}: {e}")
                continue
        
        # Enhanced duplicate detection - multiple criteria
        seen = set()
        unique_articles = []
        for article in merged_articles:
            title = article.get('title', '').strip().lower()
            link = article.get('link', '').strip()
            
            # Create multiple keys for better duplicate detection
            title_key = title[:50] if title else ''  # First 50 chars of title
            link_key = link.split('?')[0] if link else ''  # URL without query params
            
            # Combined key for duplicate detection
            key = (title_key, link_key)
            
            # Also check for similar titles (basic similarity)
            is_duplicate = False
            if title and len(title) > 10:
                for existing_article in unique_articles:
                    existing_title = existing_article.get('title', '').strip().lower()
                    if existing_title and len(existing_title) > 10:
                        # Check if titles are very similar (>80% overlap)
                        title_words = set(title.split())
                        existing_words = set(existing_title.split())
                        if title_words and existing_words:
                            overlap = len(title_words.intersection(existing_words))
                            similarity = overlap / max(len(title_words), len(existing_words))
                            if similarity > 0.8:
                                is_duplicate = True
                                break
            
            if key not in seen and not is_duplicate:
                seen.add(key)
                unique_articles.append(article)
        
        merged_metadata["count"] = len(unique_articles)
        merged_metadata["duplicates_removed"] = len(merged_articles) - len(unique_articles)
        
        # Save merged file
        final_data = {
            "metadata": merged_metadata,
            "articles": unique_articles
        }
        
        with open(final_output, 'w', encoding='utf-8') as f:
            json.dump(final_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ Merged {len(temp_files)} files into {final_output}")
        logger.info(f"   📊 Total articles: {len(unique_articles)} (removed {merged_metadata['duplicates_removed']} duplicates)")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error merging files for {final_category}: {e}")
        return False

def step1_fetch_news(categories: List[str], data_dir: str, language: str, country: str) -> int:
    """Step 1: Fetch news for all categories (same as main.py)"""
    logger.info("\n" + "="*60)
    logger.info("📰 STEP 1: FETCHING NEWS (WITH MERGING)")
    logger.info("="*60)
    
    # Group categories by their final mapped category to handle merging
    category_groups = {}
    for category in categories:
        final_category = map_source_to_final_category(category)
        if final_category not in category_groups:
            category_groups[final_category] = []
        category_groups[final_category].append(category)
    
    logger.info(f"📊 Category mapping summary:")
    for final_cat, source_cats in category_groups.items():
        if len(source_cats) > 1:
            logger.info(f"   🔄 '{final_cat}' ← {source_cats} (WILL MERGE)")
        else:
            logger.info(f"   ✅ '{final_cat}' ← {source_cats[0]}")
    
    # Fetch news for each source category first (sequentially to avoid conflicts)
    success_count = 0
    temp_files = {}  # Track temporary files for merging
    
    for category in categories:
        final_category = map_source_to_final_category(category)
        
        # Create a temporary file for this specific source category
        temp_output = os.path.join(data_dir, f"temp_news_{category.replace(' ', '_').replace('/', '_')}.json")
        
        # Fetch news for this source category
        if fetch_single_category_to_temp((category, temp_output, data_dir, language, country)):
            success_count += 1
            if final_category not in temp_files:
                temp_files[final_category] = []
            temp_files[final_category].append(temp_output)
    
    # Now merge all temp files for each final category
    merge_count = 0
    for final_category, temp_file_list in temp_files.items():
        final_output = os.path.join(data_dir, f"news_{final_category}.json")
        if merge_news_files(temp_file_list, final_output, final_category):
            merge_count += 1
        
        # Clean up temp files
        for temp_file in temp_file_list:
            try:
                os.remove(temp_file)
            except:
                pass
    
    logger.info(f"\n📊 Step 1 Summary: {success_count}/{len(categories)} source categories fetched")
    logger.info(f"📊 Merged into {merge_count} final category files")
    return success_count

async def step2_extract_and_summarize_playwright(categories: List[str], data_dir: str, max_articles: int, 
                                               timeout: int, headless: bool) -> int:
    """Step 2: Extract images and generate summaries using Playwright"""
    logger.info("\n" + "="*60)
    logger.info("🎭 STEP 2: EXTRACTING IMAGES & GENERATING SUMMARIES (PLAYWRIGHT)")
    logger.info("="*60)
    
    # Check if Playwright is available
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.error("❌ Playwright not installed. Install with: pip install playwright && playwright install chromium")
        logger.error("❌ Playwright not available. Please install with: pip install playwright && playwright install chromium")
        return False
    
    # Filter categories that have input files
    valid_categories = []
    for category in categories:
        final_category = map_source_to_final_category(category)
        input_file = os.path.join(data_dir, f"news_{final_category}.json")
        
        if os.path.exists(input_file):
            valid_categories.append((category, final_category, input_file))
        else:
            logger.warning(f"⚠️  Input file not found for source category '{category}' (expected: {input_file})")
    
    if not valid_categories:
        logger.error("❌ No valid input files found for processing")
        return 0
    
    logger.info(f"🎭 Using Playwright for {len(valid_categories)} categories")
    logger.info("💡 Playwright provides faster startup and better resource management!")
    
    success_count = 0
    
    # Use Playwright to process all categories with a single browser instance
    async with async_playwright() as p:
        # Launch browser with optimized settings
        browser = await p.chromium.launch(
            headless=headless,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-extensions",
                "--disable-popup-blocking",
                "--disable-notifications",
                "--disable-plugins",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding"
            ]
        )
        
        logger.info("🚀 Playwright browser launched, processing categories...")
        
        try:
            for i, (source_category, final_category, input_file) in enumerate(valid_categories):
                logger.info(f"\n📰 Processing category {i+1}/{len(valid_categories)}: {source_category}")
                
                output_file = os.path.join(data_dir, f"inshorts_{final_category}.json")
                
                # Create the Playwright extraction script command
                cmd = [
                    sys.executable, "scripts/generate_inshorts_playwright.py",
                    "--input", input_file,
                    "--output", output_file,
                    "--max-articles", str(max_articles),
                    "--timeout", str(timeout)
                ]
                
                if headless:
                    cmd.append("--headless")
                
                if run_command(cmd, f"Processing {source_category} articles with Playwright (mapped to {final_category})"):
                    success_count += 1
                
                # Optimized: Reduced delay between categories
                if i < len(valid_categories) - 1:
                    await asyncio.sleep(0.2)  # Reduced from 0.5 to 0.2
        
        finally:
            await browser.close()
    
    logger.info(f"\n📊 Step 2 Summary: {success_count}/{len(valid_categories)} categories processed successfully")
    logger.info("🎭 Playwright processing completed!")
    return success_count


def step3_upload_to_supabase(data_dir: str) -> bool:
    """Step 3: Upload processed data to Supabase (same as main.py)"""
    logger.info("\n" + "="*60)
    logger.info("🚀 STEP 3: UPLOADING TO SUPABASE")
    logger.info("="*60)
    
    cmd = [sys.executable, "scripts/push_inshorts_to_supabase.py"]
    
    return run_command(cmd, "Uploading all processed data to Supabase")

def cleanup_old_inshorts_files(data_dir: str):
    """Clean up old inshorts files to ensure only fresh data gets uploaded"""
    import glob
    
    logger.info("🧹 Cleaning up old inshorts files...")
    
    # Find all existing inshorts files
    inshorts_pattern = os.path.join(data_dir, "inshorts_*.json")
    old_files = glob.glob(inshorts_pattern)
    
    if old_files:
        logger.info(f"   Found {len(old_files)} old inshorts files to remove:")
        for file_path in old_files:
            try:
                os.remove(file_path)
                logger.info(f"   🗑️  Removed: {os.path.basename(file_path)}")
            except Exception as e:
                logger.warning(f"   ⚠️  Could not remove {os.path.basename(file_path)}: {e}")
        logger.info("✅ Cleanup completed - only fresh files will be uploaded")
    else:
        logger.info("   No old inshorts files found")

def check_prerequisites():
    """Check if all required files and dependencies exist"""
    logger.info("🔍 Checking prerequisites...")
    
    required_files = [
        "app/news_service.py",  # Updated: now using merged news service
        "scripts/generate_inshorts_playwright.py",
        "scripts/push_inshorts_to_supabase.py"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        logger.error(f"❌ Missing required files: {', '.join(missing_files)}")
        return False
    
    # Check if data directory exists, create if not
    if not os.path.exists("data"):
        logger.info("📁 Creating data directory...")
        os.makedirs("data", exist_ok=True)
    
    # Check Playwright installation
    try:
        import playwright
        logger.info("✅ Playwright is installed")
    except ImportError:
        logger.warning("⚠️  Playwright not installed. Install with: pip install playwright && playwright install chromium")
        logger.error("❌ Playwright is required for this application to function")
    
    logger.info("✅ Prerequisites check passed")
    return True

def print_summary(args, step1_success: int, step2_success: int, step3_success: bool):
    """Print final summary of the workflow"""
    logger.info("\n" + "="*60)
    logger.info("📋 PLAYWRIGHT WORKFLOW SUMMARY")
    logger.info("="*60)
    
    total_categories = len(args.categories)
    
    if not args.skip_fetch:
        logger.info(f"📰 Step 1 (Fetch): {step1_success}/{total_categories} categories")
    else:
        logger.info("📰 Step 1 (Fetch): SKIPPED")
    
    if not args.skip_extract:
        logger.info(f"🎭 Step 2 (Extract with Playwright): {step2_success}/{total_categories} categories")
    else:
        logger.info("🎭 Step 2 (Extract with Playwright): SKIPPED")
    
    if not args.skip_supabase:
        status = "SUCCESS" if step3_success else "FAILED"
        logger.info(f"🚀 Step 3 (Upload): {status}")
    else:
        logger.info("🚀 Step 3 (Upload): SKIPPED")
    
    logger.info(f"\n📊 Categories processed: {', '.join(args.categories)}")
    logger.info(f"📈 Max articles per category: {args.max_articles}")
    logger.info(f"🎭 Browser engine: Playwright")

def cleanup_old_data():
    """Delete all JSON files in data folder to ensure fresh extraction"""
    data_dir = Path("data")
    json_files = list(data_dir.glob("*.json"))
    
    if json_files:
        logger.info(f"🧹 Cleaning up {len(json_files)} old JSON files...")
        for json_file in json_files:
            try:
                json_file.unlink()
                logger.info(f"   ✅ Deleted: {json_file.name}")
            except Exception as e:
                logger.warning(f"   ⚠️ Could not delete {json_file.name}: {e}")
        logger.info("🧹 Cleanup completed - fresh data will be generated")
    else:
        logger.info("🧹 No old JSON files found - starting fresh")

async def main():
    """Main function to orchestrate the complete workflow with Playwright"""
    args = parse_args()
    
    # Handle headless override
    if args.no_headless:
        args.headless = False
    
    logger.info("🎭 Starting Complete News Processing Workflow with PLAYWRIGHT")
    
    # Clean up old data files first
    cleanup_old_data()
    logger.info(f"📂 Data directory: {args.data_dir}")
    logger.info(f"📰 Categories: {', '.join(args.categories)}")
    logger.info(f"📊 Max articles per category: {args.max_articles}")
    logger.info(f"🖥️  Browser mode: {'Headless' if args.headless else 'GUI'}")
    logger.info(f"🎭 Browser engine: Playwright")
    
    # Check prerequisites
    if not check_prerequisites():
        logger.error("❌ Prerequisites check failed. Exiting.")
        return 1
    
    # Clean up old inshorts files to ensure only fresh data gets uploaded
    cleanup_old_inshorts_files(args.data_dir)
    
    start_time = time.time()
    step1_success = 0
    step2_success = 0
    step3_success = False
    
    try:
        # Step 1: Fetch News (same as main.py)
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
        
        # Step 2: Extract Images and Generate Summaries with Playwright
        if not args.skip_extract:
            step2_success = await step2_extract_and_summarize_playwright(
                args.categories,
                args.data_dir,
                args.max_articles,
                args.timeout,
                args.headless
            )
            if step2_success == 0:
                logger.error("❌ No articles were processed successfully. Stopping workflow.")
                return 1
        else:
            logger.info("⏭️  Skipping Step 2: Image extraction and summarization")
        
        # Step 3: Upload to Supabase (same as main.py)
        if not args.skip_supabase:
            step3_success = step3_upload_to_supabase(args.data_dir)
        else:
            logger.info("⏭️  Skipping Step 3: Supabase upload")
            step3_success = True
        
        # Print summary
        end_time = time.time()
        duration = end_time - start_time
        
        print_summary(args, step1_success, step2_success, step3_success)
        
        logger.info(f"\n⏱️  Total execution time: {duration:.1f} seconds")
        logger.info(f"🎭 Playwright performance benefits: Faster startup, better resource management")
        
        # Determine exit code
        if args.skip_supabase:
            if args.skip_extract or step2_success > 0:
                logger.info("🎉 Playwright workflow completed successfully!")
                return 0
            else:
                logger.error("❌ Playwright workflow failed!")
                return 1
        else:
            if step3_success and (args.skip_extract or step2_success > 0):
                logger.info("🎉 Playwright workflow completed successfully!")
                return 0
            else:
                logger.error("❌ Playwright workflow failed!")
                return 1
                
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Playwright workflow interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"\n❌ Unexpected error in Playwright workflow: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))