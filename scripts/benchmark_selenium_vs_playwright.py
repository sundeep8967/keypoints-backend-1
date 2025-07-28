#!/usr/bin/env python3
"""
Benchmark test comparing Selenium vs Playwright performance for news article extraction.
Tests startup time, page loading, and content extraction speed.
"""

import os
import sys
import time
import asyncio
import logging
from pathlib import Path
from typing import Dict, List
import statistics

# Add the parent directory to sys.path
sys.path.append(str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SeleniumBenchmark:
    """Benchmark Selenium performance"""
    
    def __init__(self):
        self.driver = None
        self.startup_time = 0
        self.extraction_times = []
    
    def setup_browser(self):
        """Setup Selenium browser and measure startup time"""
        start_time = time.time()
        
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            from webdriver_manager.chrome import ChromeDriverManager
            
            options = Options()
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-popup-blocking")
            options.add_argument("--disable-notifications")
            options.add_argument("--disable-infobars")
            options.add_argument("--mute-audio")
            options.add_argument("--disable-plugins")
            options.add_argument("--disable-background-timer-throttling")
            options.add_argument("--disable-backgrounding-occluded-windows")
            options.add_argument("--disable-renderer-backgrounding")
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.set_page_load_timeout(20)
            
            self.startup_time = time.time() - start_time
            logger.info(f"🔧 Selenium startup time: {self.startup_time:.2f}s")
            return True
            
        except Exception as e:
            logger.error(f"❌ Selenium setup failed: {e}")
            return False
    
    def extract_content(self, url: str) -> Dict:
        """Extract content from URL and measure time"""
        start_time = time.time()
        
        try:
            # Navigate to URL
            self.driver.get(url)
            time.sleep(2)  # Wait for page load
            
            # Extract content
            title = self.driver.title
            current_url = self.driver.current_url
            
            # Extract Open Graph image
            og_image = None
            try:
                og_tags = self.driver.find_elements("xpath", "//meta[@property='og:image']")
                if og_tags:
                    og_image = og_tags[0].get_attribute("content")
            except:
                pass
            
            # Extract description
            description = None
            try:
                desc_tags = self.driver.find_elements("xpath", "//meta[@name='description']")
                if desc_tags:
                    description = desc_tags[0].get_attribute("content")
            except:
                pass
            
            # Extract page text
            page_text = ""
            try:
                page_text = self.driver.find_element("tag name", "body").text[:500]
            except:
                pass
            
            extraction_time = time.time() - start_time
            self.extraction_times.append(extraction_time)
            
            return {
                'success': True,
                'title': title,
                'url': current_url,
                'image': og_image,
                'description': description[:100] + "..." if description else None,
                'text_length': len(page_text),
                'extraction_time': extraction_time
            }
            
        except Exception as e:
            extraction_time = time.time() - start_time
            self.extraction_times.append(extraction_time)
            return {
                'success': False,
                'error': str(e),
                'extraction_time': extraction_time
            }
    
    def cleanup(self):
        """Cleanup browser"""
        if self.driver:
            self.driver.quit()
    
    def get_stats(self):
        """Get performance statistics"""
        if not self.extraction_times:
            return {}
        
        return {
            'startup_time': self.startup_time,
            'avg_extraction_time': statistics.mean(self.extraction_times),
            'min_extraction_time': min(self.extraction_times),
            'max_extraction_time': max(self.extraction_times),
            'total_extractions': len(self.extraction_times)
        }

class PlaywrightBenchmark:
    """Benchmark Playwright performance"""
    
    def __init__(self):
        self.browser = None
        self.page = None
        self.startup_time = 0
        self.extraction_times = []
    
    async def setup_browser(self):
        """Setup Playwright browser and measure startup time"""
        start_time = time.time()
        
        try:
            from playwright.async_api import async_playwright
            
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-extensions",
                    "--disable-popup-blocking",
                    "--disable-notifications",
                    "--disable-plugins",
                    "--disable-background-timer-throttling"
                ]
            )
            self.page = await self.browser.new_page()
            await self.page.set_viewport_size({"width": 1280, "height": 720})
            
            self.startup_time = time.time() - start_time
            logger.info(f"🔧 Playwright startup time: {self.startup_time:.2f}s")
            return True
            
        except ImportError:
            logger.error("❌ Playwright not installed. Install with: pip install playwright && playwright install chromium")
            return False
        except Exception as e:
            logger.error(f"❌ Playwright setup failed: {e}")
            return False
    
    async def extract_content(self, url: str) -> Dict:
        """Extract content from URL and measure time"""
        start_time = time.time()
        
        try:
            # Navigate to URL
            await self.page.goto(url, wait_until="domcontentloaded", timeout=20000)
            await self.page.wait_for_timeout(2000)  # Wait for page load
            
            # Extract content
            title = await self.page.title()
            current_url = self.page.url
            
            # Extract Open Graph image
            og_image = None
            try:
                og_element = await self.page.query_selector("meta[property='og:image']")
                if og_element:
                    og_image = await og_element.get_attribute("content")
            except:
                pass
            
            # Extract description
            description = None
            try:
                desc_element = await self.page.query_selector("meta[name='description']")
                if desc_element:
                    description = await desc_element.get_attribute("content")
            except:
                pass
            
            # Extract page text
            page_text = ""
            try:
                page_text = await self.page.inner_text("body")
                page_text = page_text[:500]
            except:
                pass
            
            extraction_time = time.time() - start_time
            self.extraction_times.append(extraction_time)
            
            return {
                'success': True,
                'title': title,
                'url': current_url,
                'image': og_image,
                'description': description[:100] + "..." if description else None,
                'text_length': len(page_text),
                'extraction_time': extraction_time
            }
            
        except Exception as e:
            extraction_time = time.time() - start_time
            self.extraction_times.append(extraction_time)
            return {
                'success': False,
                'error': str(e),
                'extraction_time': extraction_time
            }
    
    async def cleanup(self):
        """Cleanup browser"""
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()
    
    def get_stats(self):
        """Get performance statistics"""
        if not self.extraction_times:
            return {}
        
        return {
            'startup_time': self.startup_time,
            'avg_extraction_time': statistics.mean(self.extraction_times),
            'min_extraction_time': min(self.extraction_times),
            'max_extraction_time': max(self.extraction_times),
            'total_extractions': len(self.extraction_times)
        }

def run_selenium_benchmark(test_urls: List[str]) -> Dict:
    """Run Selenium benchmark"""
    logger.info("🔍 Starting Selenium benchmark...")
    
    selenium_bench = SeleniumBenchmark()
    
    try:
        if not selenium_bench.setup_browser():
            return {'error': 'Failed to setup Selenium'}
        
        results = []
        for i, url in enumerate(test_urls):
            logger.info(f"📰 Selenium: Processing URL {i+1}/{len(test_urls)}")
            result = selenium_bench.extract_content(url)
            results.append(result)
            time.sleep(0.5)  # Small delay between requests
        
        stats = selenium_bench.get_stats()
        stats['results'] = results
        stats['success_rate'] = sum(1 for r in results if r['success']) / len(results)
        
        return stats
        
    finally:
        selenium_bench.cleanup()

async def run_playwright_benchmark(test_urls: List[str]) -> Dict:
    """Run Playwright benchmark"""
    logger.info("🔍 Starting Playwright benchmark...")
    
    playwright_bench = PlaywrightBenchmark()
    
    try:
        if not await playwright_bench.setup_browser():
            return {'error': 'Failed to setup Playwright'}
        
        results = []
        for i, url in enumerate(test_urls):
            logger.info(f"📰 Playwright: Processing URL {i+1}/{len(test_urls)}")
            result = await playwright_bench.extract_content(url)
            results.append(result)
            await asyncio.sleep(0.5)  # Small delay between requests
        
        stats = playwright_bench.get_stats()
        stats['results'] = results
        stats['success_rate'] = sum(1 for r in results if r['success']) / len(results)
        
        return stats
        
    finally:
        await playwright_bench.cleanup()

def print_comparison(selenium_stats: Dict, playwright_stats: Dict):
    """Print detailed comparison"""
    logger.info("\n" + "="*60)
    logger.info("📊 SELENIUM vs PLAYWRIGHT BENCHMARK RESULTS")
    logger.info("="*60)
    
    if 'error' in selenium_stats:
        logger.error(f"❌ Selenium: {selenium_stats['error']}")
    else:
        logger.info(f"🔧 Selenium Results:")
        logger.info(f"   Startup time: {selenium_stats['startup_time']:.2f}s")
        logger.info(f"   Avg extraction: {selenium_stats['avg_extraction_time']:.2f}s")
        logger.info(f"   Min extraction: {selenium_stats['min_extraction_time']:.2f}s")
        logger.info(f"   Max extraction: {selenium_stats['max_extraction_time']:.2f}s")
        logger.info(f"   Success rate: {selenium_stats['success_rate']:.1%}")
    
    if 'error' in playwright_stats:
        logger.error(f"❌ Playwright: {playwright_stats['error']}")
    else:
        logger.info(f"\n🎭 Playwright Results:")
        logger.info(f"   Startup time: {playwright_stats['startup_time']:.2f}s")
        logger.info(f"   Avg extraction: {playwright_stats['avg_extraction_time']:.2f}s")
        logger.info(f"   Min extraction: {playwright_stats['min_extraction_time']:.2f}s")
        logger.info(f"   Max extraction: {playwright_stats['max_extraction_time']:.2f}s")
        logger.info(f"   Success rate: {playwright_stats['success_rate']:.1%}")
    
    # Calculate improvements
    if 'error' not in selenium_stats and 'error' not in playwright_stats:
        startup_improvement = ((selenium_stats['startup_time'] - playwright_stats['startup_time']) / selenium_stats['startup_time']) * 100
        extraction_improvement = ((selenium_stats['avg_extraction_time'] - playwright_stats['avg_extraction_time']) / selenium_stats['avg_extraction_time']) * 100
        
        logger.info(f"\n🚀 PERFORMANCE COMPARISON:")
        logger.info(f"   Startup time: Playwright is {startup_improvement:.1f}% faster")
        logger.info(f"   Extraction time: Playwright is {extraction_improvement:.1f}% faster")
        
        if startup_improvement > 0 and extraction_improvement > 0:
            logger.info(f"✅ Playwright is faster in both startup and extraction!")
        elif startup_improvement > 0:
            logger.info(f"⚡ Playwright has faster startup but similar extraction speed")
        else:
            logger.info(f"🤔 Performance is similar between both tools")

async def main():
    """Main benchmark function"""
    logger.info("🏁 Starting Selenium vs Playwright Benchmark")
    
    # Test URLs - mix of different news sites
    test_urls = [
        "https://www.bbc.com/news",
        "https://www.cnn.com",
        "https://www.reuters.com",
        "https://techcrunch.com",
        "https://www.theguardian.com"
    ]
    
    logger.info(f"🎯 Testing with {len(test_urls)} URLs")
    
    # Run Selenium benchmark
    selenium_stats = run_selenium_benchmark(test_urls)
    
    # Run Playwright benchmark
    playwright_stats = await run_playwright_benchmark(test_urls)
    
    # Print comparison
    print_comparison(selenium_stats, playwright_stats)
    
    logger.info("\n💡 RECOMMENDATION:")
    if 'error' in playwright_stats:
        logger.info("   Stick with optimized Selenium (Playwright not available)")
    elif 'error' in selenium_stats:
        logger.info("   Consider migrating to Playwright (Selenium issues)")
    else:
        startup_diff = selenium_stats['startup_time'] - playwright_stats['startup_time']
        extraction_diff = selenium_stats['avg_extraction_time'] - playwright_stats['avg_extraction_time']
        
        if startup_diff > 1 and extraction_diff > 0.5:
            logger.info("   🚀 Playwright shows significant performance gains - consider migration")
        elif startup_diff > 0.5:
            logger.info("   ⚡ Playwright is faster but gains are moderate - current setup is fine")
        else:
            logger.info("   ✅ Current Selenium setup performs well - no urgent need to migrate")

if __name__ == "__main__":
    asyncio.run(main())