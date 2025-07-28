#!/usr/bin/env python3
"""
Script to generate Inshorts-style news summaries using Playwright (faster than Selenium).
Uses Playwright for better performance, faster startup, and more efficient resource management.
"""

import os
import json
import argparse
import logging
import sys
import time
import asyncio
from pathlib import Path
from typing import Dict, List, Optional
import traceback
import re
import hashlib
import threading

# Add the parent directory to sys.path
sys.path.append(str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Generate Inshorts-style news summaries using Playwright")
    
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

async def extract_article_details_playwright(url: str, page, timeout: int = 10) -> Dict:
    """
    Extract article details using Playwright.
    
    Args:
        url: URL of the article
        page: Playwright page instance
        timeout: Timeout in seconds for loading the page
        
    Returns:
        Dictionary with article details
    """
    try:
        # Navigate to the URL
        logger.info(f"🎭 Navigating to: {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=timeout*1000)
        
        # Wait for page to load
        await page.wait_for_timeout(2000)
        
        # Get the current URL (after any redirects)
        current_url = page.url
        logger.info(f"Current URL after redirects: {current_url}")
        
        # HANDLE GOOGLE NEWS REDIRECTS - Improved with Playwright
        if "news.google.com" in current_url:
            logger.info("🔄 Detected Google News page, attempting to click through to actual article...")
            try:
                # Strategy: Try multiple selectors to find article links
                selectors_to_try = [
                    "article a[href*='http']:not([href*='google.com']):not([href*='youtube.com'])",
                    "a[data-n-tid]:not([href*='google.com'])",
                    "[role='article'] a[href*='http']:not([href*='google.com'])",
                    "h3 a[href*='http']:not([href*='google.com'])",
                    "h4 a[href*='http']:not([href*='google.com'])",
                    "a[href*='http']:not([href*='google.com']):not([href*='youtube.com']):not([href*='facebook.com'])",
                    "a[href^='http']:not([href*='google'])"
                ]
                
                article_links = []
                for selector in selectors_to_try:
                    try:
                        elements = await page.query_selector_all(selector)
                        if elements:
                            logger.info(f"✅ Found {len(elements)} links using selector: {selector}")
                            for element in elements[:10]:  # Check first 10 links
                                href = await element.get_attribute('href')
                                if href and _is_valid_article_url(href):
                                    article_links.append(href)
                            if article_links:
                                break
                    except Exception as e:
                        logger.debug(f"Selector failed: {selector} - {e}")
                        continue
                
                if article_links:
                    # Navigate to the first valid article link
                    actual_url = article_links[0]
                    logger.info(f"🔗 Found valid article link: {actual_url}")
                    
                    await page.goto(actual_url, wait_until="domcontentloaded", timeout=timeout*1000)
                    await page.wait_for_timeout(2000)
                    
                    current_url = page.url
                    logger.info(f"✅ Redirected to actual article: {current_url}")
                else:
                    logger.warning("❌ No valid article links found on Google News page")
                    
            except Exception as e:
                logger.warning(f"❌ Error handling Google News redirect: {e}")
        
        # Extract Open Graph image
        og_image = None
        twitter_image = None
        
        # Try to find Open Graph image
        try:
            og_element = await page.query_selector("meta[property='og:image']")
            if og_element:
                og_image = await og_element.get_attribute("content")
                logger.info(f"Found OG image: {og_image}")
        except:
            pass
        
        # Try to find Twitter card image
        try:
            twitter_element = await page.query_selector("meta[name='twitter:image']")
            if twitter_element:
                twitter_image = await twitter_element.get_attribute("content")
                logger.info(f"Found Twitter image: {twitter_image}")
        except:
            pass
        
        # Extract the page title
        title = await page.title()
        
        # Enhanced image extraction with quality scoring
        best_image = None
        try:
            img_elements = await page.query_selector_all("img")
            image_candidates = []
            
            for img in img_elements[:30]:  # Check more images
                try:
                    src = await img.get_attribute("src")
                    if not src or not src.startswith(("http://", "https://")):
                        continue
                    
                    # Get image attributes
                    alt_text = await img.get_attribute("alt") or ""
                    width = await img.get_attribute("width")
                    height = await img.get_attribute("height")
                    class_name = await img.get_attribute("class") or ""
                    
                    # Calculate image quality score
                    score = calculate_image_quality_score(src, alt_text, width, height, class_name)
                    
                    # Get dimensions
                    try:
                        w = int(width) if width else 0
                        h = int(height) if height else 0
                        area = w * h if w and h else 0
                    except (ValueError, TypeError):
                        area = 0
                    
                    image_candidates.append({
                        'src': src,
                        'score': score,
                        'area': area,
                        'alt': alt_text,
                        'width': w,
                        'height': h
                    })
                    
                except Exception as e:
                    continue
            
            # Sort by quality score first, then by area
            image_candidates.sort(key=lambda x: (x['score'], x['area']), reverse=True)
            
            # Find the best valid image
            for candidate in image_candidates:
                if is_valid_news_image(candidate):
                    best_image = candidate['src']
                    logger.info(f"Selected image with score {candidate['score']}: {candidate['src'][:50]}...")
                    break
                    
        except Exception as e:
            logger.debug(f"Error in enhanced image extraction: {e}")
        
        # Choose the best image with fallback hierarchy
        image_url = og_image or twitter_image or best_image
        
        # Extract the page text
        try:
            page_text = await page.inner_text("body")
        except:
            page_text = ""
        
        # Try to extract description
        description = ""
        try:
            desc_element = await page.query_selector("meta[name='description']")
            if desc_element:
                description = await desc_element.get_attribute("content")
        except:
            pass
        
        # If no description found, try Open Graph description
        if not description:
            try:
                og_desc_element = await page.query_selector("meta[property='og:description']")
                if og_desc_element:
                    description = await og_desc_element.get_attribute("content")
            except:
                pass
        
        # If still no description, extract the first paragraph
        if not description:
            try:
                paragraphs = await page.query_selector_all("p")
                for p in paragraphs[:5]:  # Check first 5 paragraphs
                    p_text = await p.inner_text()
                    p_text = p_text.strip()
                    if p_text and len(p_text) > 50:
                        description = p_text
                        break
            except:
                pass
        
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
    """Generate an enhanced summary with better content filtering and Indian context awareness"""
    try:
        # Enhanced text cleaning - remove navigation, ads, boilerplate
        lines = text.split('\n')
        
        # Patterns to remove (common website boilerplate)
        removal_patterns = [
            'skip to', 'click here', 'read more', 'subscribe', 'newsletter',
            'cookie', 'privacy policy', 'terms of service', 'advertisement',
            'follow us', 'share this', 'related articles', 'trending now',
            'breaking news', 'live updates', 'watch video', 'photo gallery',
            'also read', 'you may like', 'recommended', 'sponsored content'
        ]
        
        # Filter lines more intelligently
        filtered_lines = []
        for line in lines:
            line = line.strip()
            
            # Skip very short lines
            if len(line) < 20:
                continue
                
            # Skip lines that are likely navigation/boilerplate
            line_lower = line.lower()
            is_boilerplate = any(pattern in line_lower for pattern in removal_patterns)
            
            # Skip lines that are all caps (likely headers/navigation)
            if line.isupper() and len(line) > 10:
                continue
                
            # Skip lines with too many special characters (likely ads/formatting)
            special_char_ratio = sum(1 for c in line if not c.isalnum() and c != ' ') / len(line)
            if special_char_ratio > 0.3:
                continue
            
            # Keep good content lines
            if not is_boilerplate and len(line) > 30:
                filtered_lines.append(line)
        
        # Join the filtered lines
        cleaned_text = ' '.join(filtered_lines)
        
        # Simple sentence splitting based on common sentence endings
        def split_into_sentences(text):
            sentences = []
            current = ""
            for char in text:
                current += char
                if char in ['.', '!', '?'] and len(current.strip()) > 10:
                    sentences.append(current.strip())
                    current = ""
            
            if current.strip():
                sentences.append(current.strip())
                
            return sentences
        
        # Split the text into sentences
        sentences = split_into_sentences(cleaned_text)
        
        # Indian context keywords for prioritization
        indian_context_keywords = [
            'india', 'indian', 'bengaluru', 'bangalore', 'karnataka',
            'mumbai', 'delhi', 'chennai', 'hyderabad', 'pune', 'kolkata',
            'rupee', 'crore', 'lakh', 'pm modi', 'prime minister',
            'government', 'parliament', 'supreme court', 'bjp', 'congress'
        ]
        
        # Score sentences for relevance
        scored_sentences = []
        for sentence in sentences:
            if len(sentence.split()) < 5:  # Skip very short sentences
                continue
                
            score = 0
            sentence_lower = sentence.lower()
            
            # Boost score for Indian context
            for keyword in indian_context_keywords:
                if keyword in sentence_lower:
                    score += 10
            
            # Boost score for sentences with numbers/dates (often important facts)
            import re
            if re.search(r'\d+', sentence):
                score += 5
            
            # Boost score for sentences with proper nouns (names, places)
            words = sentence.split()
            proper_nouns = sum(1 for word in words if word[0].isupper() and len(word) > 2)
            score += proper_nouns * 2
            
            # Prefer sentences from early in the text
            position_bonus = max(0, 10 - sentences.index(sentence))
            score += position_bonus
            
            scored_sentences.append((sentence, score))
        
        # Sort by score (highest first)
        scored_sentences.sort(key=lambda x: x[1], reverse=True)
        
        # Build summary from highest-scoring sentences
        summary = ""
        word_count = 0
        used_sentences = []
        
        for sentence, score in scored_sentences:
            words = sentence.split()
            if word_count + len(words) <= max_words:
                used_sentences.append(sentence)
                word_count += len(words)
            elif word_count < max_words * 0.8:  # If we haven't used 80% of words, try partial
                remaining_words = max_words - word_count
                if remaining_words > 5:  # Only if we can add meaningful content
                    partial_sentence = " ".join(words[:remaining_words]) + "..."
                    used_sentences.append(partial_sentence)
                break
            else:
                break
        
        # Reorder sentences to maintain logical flow (by original position)
        if used_sentences:
            # Sort by original position in text
            original_order = []
            for used_sentence in used_sentences:
                for i, (original_sentence, _) in enumerate(scored_sentences):
                    if used_sentence.startswith(original_sentence[:50]):  # Match by first 50 chars
                        original_order.append((i, used_sentence))
                        break
            
            original_order.sort(key=lambda x: x[0])
            summary = " ".join([sentence for _, sentence in original_order])
        
        # If no sentences were found or summary is empty, use a simple word-based approach
        if not summary:
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

async def process_single_article_playwright(article: Dict, page, timeout: int, summary_length: int) -> Dict:
    """Process a single article using Playwright"""
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
        
        # Extract article details using Playwright
        article_details = await extract_article_details_playwright(url, page, timeout)
        
        # Generate and validate summary
        summary = None
        
        # Try multiple content sources for summary generation
        content_sources = [
            article_details['text_excerpt'],
            article_details['description'],
            title  # Fallback to title if no content
        ]
        
        for content in content_sources:
            if content and len(content.strip()) > 50:
                candidate_summary = generate_summary(content, summary_length)
                
                # Validate summary quality
                if validate_summary_quality(candidate_summary, title):
                    summary = candidate_summary
                    logger.debug(f"✅ Generated quality summary: {summary[:50]}...")
                    break
                else:
                    logger.debug(f"⚠️ Summary failed validation, trying next source...")
        
        # Final fallback
        if not summary:
            summary = "No quality content available for summarization."
        
        # Generate a unique ID for the article
        article_id = generate_article_id(url, title, source)
        
        # Calculate content quality score
        quality_score = calculate_content_quality_score(
            title, summary, article_details['image_url'], 
            article_details['description'], source
        )
        
        # Create Inshorts-style article with quality score
        processed_article = {
            'id': article_id,
            'title': title,
            'source': source,
            'url': article_details['resolved_url'] or url,
            'image_url': article_details['image_url'],
            'summary': summary,
            'published': published,
            'quality_score': quality_score
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

async def process_news_data_playwright(news_data: Dict, max_articles: int, timeout: int, summary_length: int, headless: bool) -> List[Dict]:
    """Process news data using Playwright for better performance"""
    processed_articles = []
    
    if 'articles' not in news_data:
        logger.error("No 'articles' field found in the news data")
        return processed_articles
    
    # Limit the number of articles to process
    articles_to_process = news_data['articles'][:max_articles]
    logger.info(f"🎭 Processing {len(articles_to_process)} articles with PLAYWRIGHT")
    
    # PERFORMANCE OPTIMIZATION: Track processing metrics
    start_time = time.time()
    successful_articles = 0
    
    # Check if Playwright is available
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.error("❌ Playwright not installed. Install with: pip install playwright && playwright install chromium")
        return processed_articles
    
    # Use Playwright for processing
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
        
        # Create a new page
        page = await browser.new_page()
        await page.set_viewport_size({"width": 1280, "height": 720})
        
        try:
            for i, article in enumerate(articles_to_process):
                logger.info(f"📰 Article {i+1}/{len(articles_to_process)}")
                
                result = await process_single_article_playwright(article, page, timeout, summary_length)
                processed_articles.append(result)
                
                if 'error' not in result:
                    successful_articles += 1
                
                # Small delay between articles
                if i < len(articles_to_process) - 1:
                    await asyncio.sleep(0.3)  # Faster than Selenium
        
        finally:
            await page.close()
            await browser.close()
    
    # PERFORMANCE METRICS
    total_time = time.time() - start_time
    articles_per_second = successful_articles / total_time if total_time > 0 else 0
    
    logger.info(f"🏆 PLAYWRIGHT PROCESSING COMPLETE:")
    logger.info(f"   ✅ Articles processed: {successful_articles}/{len(articles_to_process)}")
    logger.info(f"   ⏱️  Total time: {total_time:.2f} seconds")
    logger.info(f"   🚀 Processing rate: {articles_per_second:.2f} articles/second")
    logger.info(f"   🎭 Playwright performance: Faster startup & better resource management")
    
    return processed_articles

def calculate_image_quality_score(src: str, alt_text: str, width: str, height: str, class_name: str) -> int:
    """Calculate quality score for an image based on multiple factors"""
    score = 0
    src_lower = src.lower()
    alt_lower = alt_text.lower()
    class_lower = class_name.lower()
    
    # Boost for news-related alt text
    news_keywords = ['news', 'article', 'story', 'report', 'photo', 'image']
    for keyword in news_keywords:
        if keyword in alt_lower:
            score += 20
            break
    
    # Boost for proper image hosting (CDN/static)
    if any(domain in src_lower for domain in ['cdn', 'static', 'images', 'img', 'media']):
        score += 30
    
    # Penalize common ad/placeholder patterns
    ad_patterns = ['ad', 'banner', 'sponsor', 'placeholder', 'logo', 'icon', 'avatar']
    for pattern in ad_patterns:
        if pattern in src_lower or pattern in class_lower:
            score -= 50
            break
    
    # Boost for reasonable dimensions
    try:
        w, h = int(width or 0), int(height or 0)
        if w >= 300 and h >= 200:  # Good size for news images
            score += 40
        elif w >= 200 and h >= 150:  # Acceptable size
            score += 20
        elif w < 100 or h < 100:  # Too small
            score -= 30
    except (ValueError, TypeError):
        pass
    
    # Boost for article-related class names
    article_classes = ['article', 'content', 'main', 'hero', 'featured']
    for cls in article_classes:
        if cls in class_lower:
            score += 15
            break
    
    return max(0, score)

def is_valid_news_image(image_candidate: dict) -> bool:
    """Validate if an image is suitable for news articles"""
    src = image_candidate['src'].lower()
    alt = image_candidate['alt'].lower()
    width = image_candidate['width']
    height = image_candidate['height']
    
    # Reject obvious non-news images
    reject_patterns = [
        'logo', 'icon', 'avatar', 'profile', 'thumbnail',
        'ad', 'banner', 'sponsor', 'widget', 'button',
        'social', 'facebook', 'twitter', 'instagram',
        'placeholder', 'default', 'blank', 'spacer'
    ]
    
    for pattern in reject_patterns:
        if pattern in src or pattern in alt:
            return False
    
    # Require minimum dimensions
    if width and height:
        if width < 200 or height < 150:
            return False
    
    # Require reasonable aspect ratio (not too wide or tall)
    if width and height and width > 0 and height > 0:
        aspect_ratio = width / height
        if aspect_ratio > 4 or aspect_ratio < 0.25:  # Too wide or too tall
            return False
    
    # Must have reasonable quality score
    if image_candidate['score'] < 10:
        return False
    
    return True

def validate_summary_quality(summary: str, title: str) -> bool:
    """Validate if the generated summary meets quality standards"""
    if not summary or len(summary.strip()) < 20:
        return False
    
    # Check if summary contains key elements from title
    title_words = set(title.lower().split())
    summary_words = set(summary.lower().split())
    
    # At least 20% overlap with title words (excluding common words)
    common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were'}
    title_meaningful = title_words - common_words
    summary_meaningful = summary_words - common_words
    
    if title_meaningful:
        overlap = len(title_meaningful.intersection(summary_meaningful))
        overlap_ratio = overlap / len(title_meaningful)
        if overlap_ratio < 0.2:  # Less than 20% overlap
            return False
    
    # Check for common boilerplate phrases
    boilerplate_phrases = [
        'click here', 'read more', 'subscribe', 'follow us',
        'terms of service', 'privacy policy', 'cookie policy'
    ]
    
    summary_lower = summary.lower()
    for phrase in boilerplate_phrases:
        if phrase in summary_lower:
            return False
    
    return True

def calculate_content_quality_score(title: str, summary: str, image_url: str, description: str, source: str) -> float:
    """
    Calculate a quality score for the article content (0-1000).
    Prioritizes breaking news, important events, and high-impact stories.
    
    Args:
        title: Article title
        summary: Generated summary
        image_url: Image URL
        description: Article description
        source: News source
        
    Returns:
        Quality score between 0-1000
    """
    score = 0.0
    
    # Combine title and summary for importance analysis
    full_text = f"{title} {summary} {description}".lower()
    
    # BREAKING/URGENT NEWS - Highest Priority (800-1000 points)
    breaking_keywords = [
        'breaking', 'urgent', 'alert', 'emergency', 'crisis', 'disaster',
        'war', 'attack', 'bomb', 'terror', 'earthquake', 'tsunami',
        'pandemic', 'outbreak', 'death', 'killed', 'died', 'accident',
        'fire', 'explosion', 'crash', 'rescue', 'evacuation'
    ]
    
    # MAJOR POLITICAL/ECONOMIC NEWS (600-800 points)
    major_political_keywords = [
        'election', 'prime minister', 'president', 'government', 'parliament',
        'budget', 'policy', 'law', 'court', 'supreme court', 'verdict',
        'resignation', 'appointed', 'cabinet', 'minister', 'opposition'
    ]
    
    # IMPORTANT SOCIAL/CULTURAL NEWS (400-600 points)
    important_social_keywords = [
        'protest', 'strike', 'rally', 'demonstration', 'movement',
        'festival', 'celebration', 'award', 'achievement', 'record',
        'innovation', 'breakthrough', 'discovery', 'launch', 'announcement'
    ]
    
    # REGIONAL IMPORTANCE - Bengaluru/India specific (200-400 points boost)
    regional_keywords = [
        'bengaluru', 'bangalore', 'karnataka', 'india', 'indian',
        'mumbai', 'delhi', 'chennai', 'hyderabad', 'pune', 'kolkata'
    ]
    
    # Check for breaking/urgent news
    breaking_score = 0
    for keyword in breaking_keywords:
        if keyword in full_text:
            breaking_score = 900  # Very high priority
            break
    
    # Check for major political/economic news
    political_score = 0
    for keyword in major_political_keywords:
        if keyword in full_text:
            political_score = max(political_score, 700)
    
    # Check for important social/cultural news
    social_score = 0
    for keyword in important_social_keywords:
        if keyword in full_text:
            social_score = max(social_score, 500)
    
    # Regional importance boost
    regional_boost = 0
    for keyword in regional_keywords:
        if keyword in full_text:
            regional_boost = 200
            break
    
    # Base content quality (0-300 points)
    base_score = 0
    
    # Title quality (0-80 points)
    if title and len(title.strip()) > 10:
        title_words = len(title.split())
        if 5 <= title_words <= 15:  # Optimal title length
            base_score += 80
        elif title_words > 3:
            base_score += 60
        else:
            base_score += 20
    
    # Summary quality (0-120 points)
    if summary and summary != "No content available for summarization.":
        summary_words = len(summary.split())
        if 30 <= summary_words <= 80:  # Optimal summary length
            base_score += 120
        elif summary_words >= 15:
            base_score += 80
        else:
            base_score += 40
    
    # Image quality (0-60 points)
    if image_url and 'placeholder' not in image_url.lower():
        if any(domain in image_url for domain in ['cdn', 'static', 'images', 'img']):
            base_score += 60  # Likely a proper image CDN
        else:
            base_score += 40
    
    # Description availability (0-40 points)
    if description and len(description.strip()) > 20:
        base_score += 40
    elif description:
        base_score += 20
    
    # Source trustworthiness multiplier (1.0x to 1.5x)
    source_multiplier = 1.5 if is_trusted_source(source) else 1.0
    
    # Calculate final score
    importance_score = max(breaking_score, political_score, social_score)
    final_score = (importance_score + base_score + regional_boost) * source_multiplier
    
    return min(final_score, 1000.0)

def is_trusted_source(source: str) -> bool:
    """Check if the source is from a trusted news organization."""
    if not source:
        return False
    
    trusted_sources = [
        'reuters', 'bbc', 'cnn', 'ap news', 'npr', 'bloomberg',
        'times of india', 'hindustan times', 'indian express', 
        'ndtv', 'news18', 'zee news', 'deccan herald', 'the hindu',
        'economic times', 'business standard', 'mint', 'livemint'
    ]
    
    source_lower = source.lower()
    return any(trusted in source_lower for trusted in trusted_sources)

def generate_article_id(url: str, title: str, source: str) -> str:
    """Generate a unique ID for an article (same as Selenium version)"""
    combined = f"{url}|{title}|{source}"
    hash_obj = hashlib.md5(combined.encode())
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

async def main():
    """Main function"""
    args = parse_args()
    
    try:
        # Load news data
        news_data = load_news_data(args.input)
        
        # Process news data to generate summaries with PLAYWRIGHT
        processed_articles = await process_news_data_playwright(
            news_data, 
            args.max_articles, 
            args.timeout,
            args.summary_length,
            args.headless
        )
        
        # Prepare output data
        output_data = {
            'metadata': {
                'source_file': args.input,
                'generation_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                'total_articles': len(processed_articles),
                'browser_engine': 'Playwright',
                'performance_benefits': [
                    'faster_startup',
                    'better_resource_management',
                    'more_efficient_processing'
                ]
            },
            'articles': processed_articles
        }
        
        # Save to JSON file
        save_to_json(output_data, args.output)
        
        return 0
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))