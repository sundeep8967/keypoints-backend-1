#!/usr/bin/env python3
"""
Browser Session Pooling for efficient Selenium operations.
Keeps browsers alive between requests to avoid startup/shutdown overhead.
"""

import logging
import time
import threading
from typing import Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

logger = logging.getLogger(__name__)

class BrowserPool:
    """
    Browser session pool that keeps browsers alive between requests.
    Provides significant performance improvements by avoiding browser startup/shutdown overhead.
    """
    
    def __init__(self, headless: bool = True, max_idle_time: int = 300):
        """
        Initialize browser pool.
        
        Args:
            headless: Run browsers in headless mode
            max_idle_time: Maximum idle time before browser restart (seconds)
        """
        self.headless = headless
        self.max_idle_time = max_idle_time
        self.driver = None
        self.last_used = None
        self._lock = threading.Lock()
        
        logger.info(f"🏊 Browser pool initialized (headless={headless}, max_idle={max_idle_time}s)")
    
    def get_driver(self):
        """
        Get a browser driver from the pool.
        Creates new browser if none exists or if current one is stale.
        
        Returns:
            WebDriver instance
        """
        with self._lock:
            # Check if we need to create or restart browser
            if self._needs_new_browser():
                self._create_new_browser()
            
            self.last_used = time.time()
            return self.driver
    
    def _needs_new_browser(self) -> bool:
        """Check if we need to create a new browser"""
        if not self.driver:
            logger.info("🆕 No browser exists, creating new one")
            return True
        
        # Check if browser is still responsive
        try:
            # Simple check to see if browser is alive
            self.driver.current_url
        except Exception as e:
            logger.warning(f"🔄 Browser unresponsive, creating new one: {e}")
            self._cleanup_driver()
            return True
        
        # Check if browser has been idle too long
        if self.last_used and (time.time() - self.last_used) > self.max_idle_time:
            logger.info(f"🕐 Browser idle for {self.max_idle_time}s, restarting for freshness")
            self._cleanup_driver()
            return True
        
        return False
    
    def _create_new_browser(self):
        """Create a new browser instance with optimized settings"""
        try:
            logger.info("🚀 Creating new optimized browser instance...")
            
            options = Options()
            # Basic stability options
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-popup-blocking")
            options.add_argument("--disable-notifications")
            options.add_argument("--disable-infobars")
            options.add_argument("--mute-audio")
            
            # PERFORMANCE OPTIMIZATIONS - Keep image extraction working
            options.add_argument("--disable-plugins")
            options.add_argument("--disable-background-timer-throttling")
            options.add_argument("--disable-backgrounding-occluded-windows")
            options.add_argument("--disable-renderer-backgrounding")
            options.add_argument("--disable-features=TranslateUI")
            options.add_argument("--disable-ipc-flooding-protection")
            
            # SESSION POOLING OPTIMIZATIONS
            options.add_argument("--disable-background-networking")
            options.add_argument("--disable-default-apps")
            options.add_argument("--disable-sync")
            options.add_argument("--metrics-recording-only")
            options.add_argument("--no-first-run")
            
            options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
            
            # Add headless mode if requested
            if self.headless:
                options.add_argument("--headless")
                options.add_argument("--disable-gpu")
            
            # Initialize Chrome WebDriver
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.set_page_load_timeout(20)
            
            logger.info("✅ Browser pool: New browser instance ready")
            
        except Exception as e:
            logger.error(f"❌ Failed to create browser: {e}")
            raise
    
    def _cleanup_driver(self):
        """Safely cleanup the current driver"""
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                logger.warning(f"Error during browser cleanup: {e}")
            finally:
                self.driver = None
    
    def reset_if_needed(self):
        """
        Reset browser if it's unresponsive or has issues.
        This is called automatically by get_driver(), but can be called manually.
        """
        with self._lock:
            if self.driver:
                try:
                    # Test if browser is responsive
                    self.driver.current_url
                    logger.debug("Browser is responsive, no reset needed")
                except Exception as e:
                    logger.warning(f"Browser needs reset: {e}")
                    self._cleanup_driver()
    
    def clear_browser_data(self):
        """Clear browser cache, cookies, etc. for fresh state"""
        if self.driver:
            try:
                logger.info("🧹 Clearing browser data...")
                self.driver.delete_all_cookies()
                self.driver.execute_script("window.localStorage.clear();")
                self.driver.execute_script("window.sessionStorage.clear();")
                logger.info("✅ Browser data cleared")
            except Exception as e:
                logger.warning(f"Error clearing browser data: {e}")
    
    def get_stats(self) -> dict:
        """Get browser pool statistics"""
        return {
            'has_browser': self.driver is not None,
            'last_used': self.last_used,
            'idle_time': time.time() - self.last_used if self.last_used else None,
            'max_idle_time': self.max_idle_time,
            'headless': self.headless
        }
    
    def cleanup(self):
        """Cleanup browser pool and close all browsers"""
        logger.info("🧹 Cleaning up browser pool...")
        with self._lock:
            self._cleanup_driver()
        logger.info("✅ Browser pool cleanup complete")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.cleanup()

# Global browser pool instance for easy access
_global_browser_pool = None

def get_global_browser_pool(headless: bool = True) -> BrowserPool:
    """
    Get or create the global browser pool instance.
    
    Args:
        headless: Run in headless mode
        
    Returns:
        BrowserPool instance
    """
    global _global_browser_pool
    if _global_browser_pool is None:
        _global_browser_pool = BrowserPool(headless=headless)
    return _global_browser_pool

def cleanup_global_browser_pool():
    """Cleanup the global browser pool"""
    global _global_browser_pool
    if _global_browser_pool:
        _global_browser_pool.cleanup()
        _global_browser_pool = None