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

# Scoring functions removed - no longer needed

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

async def extract_clean_article_content(page) -> str:
    """
    Extract clean article content from the page, filtering out navigation, ads, and boilerplate.
    Enhanced with content quality scoring and comprehensive extraction strategies.
    """
    try:
        # Content candidates
        content_candidates = []
        
        # Strategy 1: Try to find article content using semantic selectors (expanded list)
        article_selectors = [
            "article",
            "[role='main']",
            ".article-content",
            ".story-content", 
            ".post-content",
            ".entry-content",
            ".content-body",
            ".article-body",
            ".story-body",
            ".main-content",
            "#article-content",
            "#story-content",
            ".news-content",
            ".article-text",
            ".story-text",
            ".content-text",
            ".post-body",
            ".entry-body",
            ".article-wrapper",
            ".story-wrapper",
            ".content-wrapper",
            ".text-content",
            ".article-detail",
            ".story-detail",
            ".news-body",
            ".article-main",
            ".story-main",
            ".content-main",
            "#content",
            "#main-content",
            "#article",
            "#story",
            ".full-story",
            ".article-full",
            ".story-full"
        ]
        
        # Add site-specific selectors based on current URL
        current_url = page.url.lower()
        site_specific_selectors = get_site_specific_selectors(current_url)
        if site_specific_selectors:
            article_selectors = site_specific_selectors + article_selectors
            logger.info(f"🎯 Using site-specific selectors for: {current_url}")
        
        # Extract content from semantic selectors with quality scoring
        for selector in article_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    content = await element.inner_text()
                    if content and len(content.strip()) > 500:  # Increased threshold from 200 to 500
                        cleaned_content = _clean_content(content.strip())
                        if len(cleaned_content) > 300:  # Ensure cleaned content is substantial
                            content_candidates.append({
                                'content': cleaned_content,
                                'source': f"semantic_selector_{selector}",
                                'length': len(cleaned_content)
                            })
                            logger.info(f"✅ Found article content using selector: {selector} ({len(cleaned_content)} chars)")
            except:
                continue
        
        # Strategy 2: Extract meaningful paragraphs (enhanced) - Try this BEFORE meta descriptions
        try:
            paragraphs = await page.query_selector_all("p")
            meaningful_paragraphs = []
            
            for p in paragraphs:
                p_text = await p.inner_text()
                p_text = p_text.strip()
                
                # Enhanced filtering for better content
                skip_words = [
                    'subscribe', 'sign in', 'newsletter', 'follow us', 'share this',
                    'advertisement', 'sponsored', 'cookie', 'privacy policy',
                    'terms of service', 'read more', 'click here', 'related articles',
                    'also read', 'trending now', 'breaking news', 'live updates',
                    'watch video', 'photo gallery', 'you may like', 'recommended',
                    'sponsored content', 'latest news', 'more news', 'top stories',
                    'view all', 'see more', 'load more', 'show more', 'continue reading'
                ]
                
                # More comprehensive filtering
                if (len(p_text) > 50 and  # Increased from 40 to 50
                    not any(skip_word in p_text.lower() for skip_word in skip_words) and
                    not p_text.isupper() and  # Skip all-caps navigation
                    not re.match(r'^[A-Z\s]+$', p_text) and  # Skip navigation menus
                    not re.match(r'^[0-9\s\-\|\:]+$', p_text) and  # Skip date/time strings
                    not p_text.startswith(('Updated', 'Published', 'Last updated', 'Posted')) and
                    '|' not in p_text[-20:] and  # Skip lines ending with | (navigation)
                    len(p_text.split()) > 10):  # Increased from 8 to 10 words
                    
                    meaningful_paragraphs.append(p_text)
                    
                    # Collect more content for longer descriptions
                    if len(' '.join(meaningful_paragraphs)) > 1200:  # Increased from 800
                        break
            
            if meaningful_paragraphs:
                # Take more paragraphs for longer content
                paragraph_content = ' '.join(meaningful_paragraphs[:7])  # Increased from 5 to 7
                cleaned_paragraph_content = _clean_content(paragraph_content)
                if len(cleaned_paragraph_content) > 200:
                    content_candidates.append({
                        'content': cleaned_paragraph_content,
                        'source': "meaningful_paragraphs",
                        'length': len(cleaned_paragraph_content)
                    })
                    logger.info(f"✅ Extracted {len(meaningful_paragraphs)} meaningful paragraphs ({len(cleaned_paragraph_content)} chars)")
        except:
            pass
        
        # Strategy 3: Try alternative div selectors for more content
        try:
            div_selectors = [
                ".story", ".article", ".content", ".post", ".entry",
                "#story", "#article", "#content", "#post", "#entry",
                ".news-article", ".article-container", ".story-container",
                ".content-container", ".post-container", ".entry-container"
            ]
            
            for selector in div_selectors:
                element = await page.query_selector(selector)
                if element:
                    div_content = await element.inner_text()
                    if div_content and len(div_content.strip()) > 400:  # Increased threshold
                        cleaned_div_content = _clean_content(div_content.strip())
                        if len(cleaned_div_content) > 250:
                            content_candidates.append({
                                'content': cleaned_div_content,
                                'source': f"div_selector_{selector}",
                                'length': len(cleaned_div_content)
                            })
                            logger.info(f"✅ Found content using div selector {selector} ({len(cleaned_div_content)} chars)")
        except:
            pass
        
        # Strategy 4: Meta descriptions (LOWER PRIORITY - only if no substantial content found)
        try:
            # Try meta description
            desc_element = await page.query_selector("meta[name='description']")
            if desc_element:
                meta_desc = await desc_element.get_attribute("content")
                if meta_desc and len(meta_desc.strip()) > 100:  # Increased threshold from 50 to 100
                    cleaned_meta_desc = _clean_content(meta_desc.strip())
                    content_candidates.append({
                        'content': cleaned_meta_desc,
                        'source': "meta_description",
                        'length': len(cleaned_meta_desc)
                    })
                    logger.info(f"✅ Found meta description ({len(cleaned_meta_desc)} chars)")
        except:
            pass
        
        # Strategy 5: Open Graph description (LOWEST PRIORITY)
        try:
            og_desc_element = await page.query_selector("meta[property='og:description']")
            if og_desc_element:
                og_desc = await og_desc_element.get_attribute("content")
                if og_desc and len(og_desc.strip()) > 100:  # Increased threshold from 50 to 100
                    cleaned_og_desc = _clean_content(og_desc.strip())
                    content_candidates.append({
                        'content': cleaned_og_desc,
                        'source': "og_description",
                        'length': len(cleaned_og_desc)
                    })
                    logger.info(f"✅ Found OG description ({len(cleaned_og_desc)} chars)")
        except:
            pass
        
        # Select the best content based on length
        if content_candidates:
            # Sort by length (longer content is generally better)
            content_candidates.sort(key=lambda x: x['length'], reverse=True)
            
            # Try to find content that's relevant to the page title
            page_title = await page.title() if page else ""
            
            best_content = None
            
            # First, try to find title-relevant content that's also substantial (>300 chars)
            for candidate in content_candidates:
                if (validate_content_relevance(candidate['content'], page_title) and 
                    candidate['length'] > 300):
                    best_content = candidate
                    logger.info(f"🎯 Selected relevant substantial content: {candidate['source']} (length: {candidate['length']}, title-relevant: ✅)")
                    break
            
            # If no substantial title-relevant content, prefer longer content over title relevance
            if not best_content:
                # Prioritize content with length > 300 chars, even if not title-relevant
                for candidate in content_candidates:
                    if candidate['length'] > 300:
                        best_content = candidate
                        logger.info(f"🏆 Selected substantial content: {candidate['source']} (length: {candidate['length']}, title-relevant: ❓)")
                        break
                
                # Final fallback to longest content
                if not best_content:
                    best_content = content_candidates[0]
                    logger.info(f"🏆 Selected best available content: {best_content['source']} (length: {best_content['length']}, title-relevant: ❌)")
            
            # Limit length to reasonable size but allow longer descriptions
            final_content = best_content['content']
            if len(final_content) > 5000:  # Increased limit to allow longer descriptions
                # Try to cut at a sentence boundary instead of mid-sentence
                sentences = final_content[:5000].split('.')
                if len(sentences) > 1:
                    # Keep all complete sentences that fit within the limit
                    final_content = '.'.join(sentences[:-1]) + '.'
                else:
                    # If no sentence boundary found, cut at word boundary
                    words = final_content[:5000].split()
                    final_content = ' '.join(words[:-1]) + "..."
            
            return final_content
        
        # Fallback: return a message indicating no content found
        logger.warning("❌ No clean article content found")
        return "Article content could not be extracted."
        
    except Exception as e:
        logger.error(f"Error extracting article content: {e}")
        return "Error extracting article content."

def _clean_content(content: str) -> str:
    """Clean and normalize content text"""
    if not content:
        return ""
    
    # Remove excessive whitespace
    content = re.sub(r'\s+', ' ', content)
    
    # Remove common trailing patterns
    content = re.sub(r'\s*\|\s*Latest News.*$', '', content)
    content = re.sub(r'\s*\|\s*[A-Z][a-z]+\s*$', '', content)
    
    # Remove common prefixes/suffixes
    content = re.sub(r'^(Updated|Published|Last updated|Posted):\s*[^.]*\.\s*', '', content)
    content = re.sub(r'\s*(Read more|Continue reading|View full article).*$', '', content, flags=re.IGNORECASE)
    
    return content.strip()

# Content quality calculation removed - no longer needed

def generate_key_points(description: str, title: str = "") -> List[str]:
    """
    Generate key points from article description in the specified format
    """
    if not description or len(description.strip()) < 50:
        logger.warning(f"⚠️ Description too short for key points generation: {len(description.strip()) if description else 0} chars")
        return []
    
    try:
        # Clean and prepare the text
        text = description.strip()
        
        # Split into sentences
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
        
        # Filter out website UI/metadata sentences - EXPANDED LIST
        ui_patterns = [
            'show quick read', 'ai-generated', 'newsroom-reviewed', 'did our ai',
            'switch to beeps', 'read time:', 'share twitter', 'whatsapp facebook',
            'reported by:', 'published on', 'last updated', 'subscribe', 'newsletter',
            'follow us', 'click here', 'read more', 'view full article', 'continue reading',
            'related articles', 'trending now', 'breaking news updates', 'live updates',
            'photo gallery', 'watch video', 'also read', 'you may like', 'recommended',
            # Website navigation and headers
            'epaper', 'bizzbuzz', 'hmtv live', 'hans app', 'latest news', 'menu',
            'trending :', 'home >', 'entertainment', 'photo stories', 'sports',
            'editorial', 'technology', 'lifestyle', 'education & careers', 'business',
            'hyderabad', 'cricket', 'delhi region', 'karnataka', 'telangana',
            'andhra pradesh', 'visakhapatnam', 'festival of democracy',
            # Social media and sharing
            'email article', 'print article', 'telegram', 'click here to join',
            'stay updated', 'more stories', 'advertisement', 'advertise with us',
            # Website footer and legal
            'terms & conditions', 'privacy policy', 'disclaimer', 'sitemap',
            'all rights reserved', 'powered by', 'contact us', 'about us',
            'subscriber terms', 'company', 'media house limited',
            # Navigation breadcrumbs
            'news > state >', 'home > news >', 'state > karnataka >',
            # Author and timestamp patterns
            'news service |', 'am ist', 'pm ist', 'representational image'
        ]
        
        # Filter sentences that contain UI patterns
        filtered_sentences = []
        for sentence in sentences:
            sentence_lower = sentence.lower()
            is_ui_text = any(pattern in sentence_lower for pattern in ui_patterns)
            
            # Also filter sentences that look like timestamps or metadata
            if (not is_ui_text and 
                not re.match(r'.*\d{4}\s+\d{1,2}:\d{2}\s+(am|pm)', sentence_lower) and  # timestamps
                not re.match(r'.*(published|updated|reported).*\d{4}', sentence_lower) and  # publication info
                not sentence_lower.startswith(('share ', 'follow ', 'subscribe '))):  # social media
                filtered_sentences.append(sentence)
        
        sentences = filtered_sentences
        
        if len(sentences) < 2:
            return []
        
        key_points = []
        
        # Extract key entities and topics for categorization
        def extract_key_entities(sentence):
            # Look for proper nouns, organizations, locations, numbers
            entities = []
            words = sentence.split()
            
            for i, word in enumerate(words):
                # Capitalized words (likely proper nouns)
                if word[0].isupper() and len(word) > 2:
                    entities.append(word)
                # Numbers with context
                if re.search(r'\d+', word):
                    context = ' '.join(words[max(0, i-2):i+3])
                    entities.append(context.strip())
            
            return entities
        
        # Categorize sentences based on content patterns
        for i, sentence in enumerate(sentences[:5]):  # Limit to 5 key points
            if len(sentence) < 30:
                continue
                
            sentence = sentence.strip()
            if not sentence.endswith(('.', '!', '?')):
                sentence += '.'
            
            # Just add the clean sentence directly to key_points
            key_points.append(sentence)
        
        # If we have fewer than 3 key points, try to extract more
        if len(key_points) < 3 and len(sentences) > len(key_points):
            remaining_sentences = sentences[len(key_points):len(key_points)+2]
            for sentence in remaining_sentences:
                if len(sentence) > 30:
                    sentence = sentence.strip()
                    if not sentence.endswith(('.', '!', '?')):
                        sentence += '.'
                    # Just add the sentence without sub-headings
                    key_points.append(sentence)
        
        return key_points[:5]  # Return max 5 key points
        
    except Exception as e:
        logger.error(f"Error generating key points: {e}")
        return []

def validate_content_relevance(content: str, title: str) -> bool:
    """Check if extracted content is relevant to the article title"""
    if not content or not title:
        return False
    
    # Extract key terms from title
    title_terms = set(re.findall(r'\b\w{4,}\b', title.lower()))
    
    # Count how many title terms appear in content
    content_lower = content.lower()
    matching_terms = sum(1 for term in title_terms if term in content_lower)
    
    # At least 30% of title terms should appear in content
    return matching_terms >= len(title_terms) * 0.3

def is_duplicate_content(content: str, existing_articles: List[Dict]) -> bool:
    """Check if content is too similar to already processed articles"""
    content_hash = hashlib.md5(content[:200].encode()).hexdigest()
    return any(article.get('content_hash') == content_hash for article in existing_articles)

async def extract_clean_title(page, page_title: str) -> str:
    """
    Extract article title with better filtering and prioritization
    """
    try:
        # Strategy 1: Get h1 elements with smart filtering
        h1_elements = await page.query_selector_all("h1")
        candidates = []
        
        # Common generic words to deprioritize (but not exclude completely)
        generic_words = {'video', 'videos', 'news', 'breaking', 'latest', 'live', 'watch', 'photos', 'gallery'}
        
        # Words that indicate this is likely NOT the main title
        exclude_words = {'menu', 'home', 'search', 'navigation', 'subscribe', 'login', 'sign'}
        
        for h1 in h1_elements:
            try:
                title_text = await h1.inner_text()
                if not title_text or len(title_text.strip()) <= 5:
                    continue
                    
                title_text = title_text.strip()
                title_lower = title_text.lower()
                
                # Skip obvious navigation/UI elements
                if any(word in title_lower for word in exclude_words):
                    continue
                
                # Check if it's in main content area (better context)
                parent_element = await h1.query_selector("xpath=..")
                parent_class = ""
                if parent_element:
                    parent_class = (await parent_element.get_attribute("class") or "").lower()
                
                # Simple validation system
                word_count = len(title_text.split())
                
                # Skip generic single words
                if title_lower in generic_words:
                    continue
                
                # Skip very short single-word titles
                if len(title_text) < 15 and word_count == 1:
                    continue
                
                # Prefer titles in article/content areas
                in_content_area = any(keyword in parent_class for keyword in ['article', 'content', 'story', 'headline', 'main'])
                
                candidates.append({
                    'text': title_text,
                    'length': len(title_text),
                    'word_count': word_count,
                    'in_content_area': in_content_area
                })
                
            except:
                continue
        
        # Sort by content area preference, then by length and word count
        candidates.sort(key=lambda x: (x['in_content_area'], x['word_count'], x['length']), reverse=True)
        
        if candidates:
            best_title = candidates[0]['text']
            logger.info(f"✅ Using best h1 title: {best_title}")
            return clean_title_suffix(best_title)
        
        # Strategy 2: Try article-specific selectors
        article_selectors = [
            "article h1",
            ".article-title",
            ".headline",
            ".story-title",
            ".post-title",
            "[data-testid*='headline']",
            "[class*='headline']"
        ]
        
        for selector in article_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    title_text = await element.inner_text()
                    if title_text and len(title_text.strip()) > 5:
                        title_text = title_text.strip()
                        if title_text.lower() not in generic_words:
                            logger.info(f"✅ Using article selector title: {title_text}")
                            return clean_title_suffix(title_text)
            except:
                continue
        
        # Strategy 3: Try Open Graph title (but validate it's not generic)
        try:
            og_element = await page.query_selector("meta[property='og:title']")
            if og_element:
                og_title = await og_element.get_attribute("content")
                if og_title and len(og_title.strip()) > 5:
                    og_title = og_title.strip()
                    # Don't use if it's just a generic word
                    if og_title.lower() not in generic_words and len(og_title.split()) >= 2:
                        logger.info(f"✅ Using OG title: {og_title}")
                        return clean_title_suffix(og_title)
        except:
            pass
        
        # Strategy 4: Try JSON-LD structured data
        try:
            json_ld_scripts = await page.query_selector_all("script[type='application/ld+json']")
            for script in json_ld_scripts:
                try:
                    content = await script.inner_text()
                    import json
                    data = json.loads(content)
                    
                    # Handle both single objects and arrays
                    items = data if isinstance(data, list) else [data]
                    
                    for item in items:
                        if isinstance(item, dict):
                            # Look for article or news article
                            if item.get('@type') in ['Article', 'NewsArticle']:
                                headline = item.get('headline')
                                if headline and len(headline.strip()) > 5:
                                    headline = headline.strip()
                                    if headline.lower() not in generic_words:
                                        logger.info(f"✅ Using JSON-LD headline: {headline}")
                                        return clean_title_suffix(headline)
                except:
                    continue
        except:
            pass
        
        # Strategy 5: Use page title as last resort (but clean it)
        if page_title and len(page_title.strip()) > 5:
            page_title = page_title.strip()
            # Remove common suffixes from page titles
            suffixes_to_remove = [' - NDTV', ' | NDTV', ' - News', ' | News', ' - Latest News']
            for suffix in suffixes_to_remove:
                if page_title.endswith(suffix):
                    page_title = page_title[:-len(suffix)].strip()
                    break
            
            if page_title.lower() not in generic_words:
                logger.info(f"✅ Using cleaned page title: {page_title}")
                return clean_title_suffix(page_title)
        
        return "No Title Found"
        
    except Exception as e:
        logger.error(f"Error extracting title: {e}")
        return page_title or "Error Extracting Title"

def get_site_specific_selectors(url: str) -> List[str]:
    """Get site-specific content selectors based on the URL"""
    selectors = []
    
    # Indian News Sites
    if "hindustantimes.com" in url:
        selectors.extend([
            ".storyDetails",
            "#main-content", 
            ".detail",
            ".story-element-text",
            ".htImport",
            ".story-details"
        ])
    elif "timesofindia.indiatimes.com" in url:
        selectors.extend([
            ".contentwrapper",
            ".MvyrO",
            ".awuxh",
            ".HTz_b", 
            "._3WlLe",
            ".Normal",
            ".ga-headlines",
            "._1_Akb",
            ".story_content",
            "#artext",
            "[data-articlebody]",
            ".article-content",
            ".story-body"
        ])
    elif "indianexpress.com" in url:
        selectors.extend([
            ".story_details",
            ".full-details",
            "#pcl-full-content",
            ".ie-first-publish",
            ".story-element"
        ])
    elif "ndtv.com" in url:
        selectors.extend([
            ".sp-cn",
            ".story__content",
            ".ins_storybody",
            "#ins_storybody",
            ".content_text"
        ])
    elif "news18.com" in url:
        selectors.extend([
            ".article-box",
            ".story-article-box",
            ".story_content_div",
            ".article_content"
        ])
    elif "zeenews.india.com" in url:
        selectors.extend([
            ".article-box",
            ".story-text",
            "#story-text",
            ".article_content"
        ])
    elif "deccanherald.com" in url:
        selectors.extend([
            ".story-element-text",
            ".article-content",
            ".story-content",
            "#article-content"
        ])
    elif "thehindu.com" in url:
        selectors.extend([
            ".article-body",
            ".story-content",
            "#content-body-14269002",
            ".story-element"
        ])
    elif "economictimes.indiatimes.com" in url:
        selectors.extend([
            ".artText",
            ".Normal",
            "#pageContent",
            ".story_content"
        ])
    elif "livemint.com" in url:
        selectors.extend([
            ".FirstEle",
            ".paywall",
            ".story-element",
            "#container"
        ])
    elif "businesstoday.in" in url:
        selectors.extend([
            ".story-kicker",
            ".story-content",
            ".article-content",
            "#story-content"
        ])
    elif "financialexpress.com" in url:
        selectors.extend([
            ".main-story",
            ".story-content",
            ".article-content",
            "#article-content"
        ])
    elif "moneycontrol.com" in url:
        selectors.extend([
            ".content_wrapper",
            ".arti-flow",
            "#article-main",
            ".article-wrap"
        ])
    elif "business-standard.com" in url:
        selectors.extend([
            ".story-content-new",
            ".story-element-text",
            "#story-content",
            ".article-content"
        ])
    elif "scroll.in" in url:
        selectors.extend([
            ".story-element",
            ".story-content",
            "#story-content-body",
            ".article-content"
        ])
    elif "thewire.in" in url:
        selectors.extend([
            ".td-post-content",
            ".story-content",
            "#story-content",
            ".article-content"
        ])
    elif "newslaundry.com" in url:
        selectors.extend([
            ".story-content",
            ".article-content",
            "#story-content",
            ".post-content"
        ])
    elif "caravanmagazine.in" in url:
        selectors.extend([
            ".story-content",
            ".article-body",
            "#article-content",
            ".post-content"
        ])
    elif "outlookindia.com" in url:
        selectors.extend([
            ".story-content",
            ".article-content",
            "#story-content",
            ".main-content"
        ])
    elif "india.com" in url:
        selectors.extend([
            ".story-content",
            ".article-content",
            "#article-content",
            ".main-content"
        ])
    elif "firstpost.com" in url:
        selectors.extend([
            ".story-element",
            ".article-content",
            "#story-content",
            ".main-content"
        ])
    elif "news.abplive.com" in url:
        selectors.extend([
            ".story-content",
            ".article-content",
            "#story-content",
            ".main-content"
        ])
    elif "aajtak.in" in url:
        selectors.extend([
            ".story-content",
            ".article-content",
            "#story-content",
            ".main-content"
        ])
    elif "republicworld.com" in url:
        selectors.extend([
            ".story-content",
            ".article-content",
            "#story-content",
            ".main-content"
        ])
    elif "timesnownews.com" in url:
        selectors.extend([
            ".story-content",
            ".article-content",
            "#story-content",
            ".main-content"
        ])
    
    # International News Sites
    elif "cnn.com" in url:
        selectors.extend([
            ".zn-body__paragraph",
            ".el__leafmedia--sourced-paragraph",
            ".zn-body__read-all",
            ".pg-rail-tall__head"
        ])
    elif "bbc.com" in url or "bbc.co.uk" in url:
        selectors.extend([
            "[data-component='text-block']",
            ".story-body__inner",
            ".gel-body-copy",
            "#story-body"
        ])
    elif "reuters.com" in url:
        selectors.extend([
            "[data-testid='paragraph']",
            ".StandardArticleBody_body",
            ".ArticleBodyWrapper",
            ".PaywallBarrier-container"
        ])
    elif "nytimes.com" in url:
        selectors.extend([
            ".StoryBodyCompanionColumn",
            "[name='articleBody']",
            ".css-53u6y8",
            ".story-content"
        ])
    elif "washingtonpost.com" in url:
        selectors.extend([
            ".article-body",
            "[data-qa='article-body']",
            ".paywall",
            "#article-body"
        ])
    elif "wsj.com" in url:
        selectors.extend([
            ".wsj-snippet-body",
            ".article-content",
            "#articleBody",
            ".snippet-promotion"
        ])
    elif "bloomberg.com" in url:
        selectors.extend([
            "[data-module='ArticleBody']",
            ".body-content",
            ".fence-body",
            "#article-content-body"
        ])
    elif "guardian.com" in url or "theguardian.com" in url:
        selectors.extend([
            ".article-body-commercial-selector",
            ".content__article-body",
            "#maincontent",
            ".prose"
        ])
    elif "independent.co.uk" in url:
        selectors.extend([
            ".sc-1tw117-0",
            "#main",
            ".body-content",
            ".article-body"
        ])
    elif "telegraph.co.uk" in url:
        selectors.extend([
            ".article-body-text",
            "#article-body",
            ".story-body",
            ".article-content"
        ])
    elif "ap.org" in url or "apnews.com" in url:
        selectors.extend([
            ".Article",
            "[data-key='article']",
            ".story-content",
            "#article-content"
        ])
    elif "npr.org" in url:
        selectors.extend([
            "#storytext",
            ".storytext",
            ".story-content",
            "#article-content"
        ])
    elif "foxnews.com" in url:
        selectors.extend([
            ".article-body",
            ".article-text",
            "#article-content",
            ".story-content"
        ])
    elif "nbcnews.com" in url:
        selectors.extend([
            "[data-module='ArticleBody']",
            ".articleBody",
            "#article-content",
            ".story-content"
        ])
    elif "cbsnews.com" in url:
        selectors.extend([
            ".content__body",
            "#article-wrap",
            ".story-content",
            "#article-content"
        ])
    elif "abcnews.go.com" in url:
        selectors.extend([
            ".Article__Content",
            "#article-content",
            ".story-content",
            ".article-body"
        ])
    elif "usatoday.com" in url:
        selectors.extend([
            ".story-body",
            "#article-content",
            ".story-content",
            ".article-body"
        ])
    elif "politico.com" in url:
        selectors.extend([
            ".story-text",
            "#article-content",
            ".story-content",
            ".article-body"
        ])
    elif "huffpost.com" in url or "huffingtonpost.com" in url:
        selectors.extend([
            ".entry__text",
            "#article-content",
            ".story-content",
            ".article-body"
        ])
    elif "axios.com" in url:
        selectors.extend([
            ".gtm-story-text",
            "#article-content",
            ".story-content",
            ".article-body"
        ])
    elif "vox.com" in url:
        selectors.extend([
            ".c-entry-content",
            "#article-content",
            ".story-content",
            ".article-body"
        ])
    elif "buzzfeednews.com" in url:
        selectors.extend([
            ".news-article-header__body",
            "#article-content",
            ".story-content",
            ".article-body"
        ])
    elif "vice.com" in url:
        selectors.extend([
            ".article__body",
            "#article-content",
            ".story-content",
            ".article-body"
        ])
    elif "slate.com" in url:
        selectors.extend([
            ".article__content",
            "#article-content",
            ".story-content",
            ".article-body"
        ])
    elif "theatlantic.com" in url:
        selectors.extend([
            ".article-body",
            "#article-content",
            ".story-content",
            ".c-article-body"
        ])
    elif "newyorker.com" in url:
        selectors.extend([
            ".SectionBreak",
            "#article-content",
            ".story-content",
            ".article-body"
        ])
    elif "time.com" in url:
        selectors.extend([
            ".padded",
            "#article-content",
            ".story-content",
            ".article-body"
        ])
    elif "newsweek.com" in url:
        selectors.extend([
            ".article-body",
            "#article-content",
            ".story-content",
            ".main-article"
        ])
    elif "fortune.com" in url:
        selectors.extend([
            ".article-content",
            "#article-content",
            ".story-content",
            ".article-body"
        ])
    elif "forbes.com" in url:
        selectors.extend([
            ".article-body",
            "#article-content",
            ".story-content",
            ".body-container"
        ])
    elif "businessinsider.com" in url:
        selectors.extend([
            ".content-lock-content",
            "#article-content",
            ".story-content",
            ".article-body"
        ])
    elif "techcrunch.com" in url:
        selectors.extend([
            ".article-content",
            "#article-content",
            ".story-content",
            ".entry-content"
        ])
    elif "theverge.com" in url:
        selectors.extend([
            ".c-entry-content",
            "#article-content",
            ".story-content",
            ".article-body"
        ])
    elif "wired.com" in url:
        selectors.extend([
            ".article__chunks",
            "#article-content",
            ".story-content",
            ".article-body"
        ])
    elif "arstechnica.com" in url:
        selectors.extend([
            ".article-content",
            "#article-content",
            ".story-content",
            ".post-content"
        ])
    elif "engadget.com" in url:
        selectors.extend([
            ".article-text",
            "#article-content",
            ".story-content",
            ".article-body"
        ])
    elif "gizmodo.com" in url:
        selectors.extend([
            ".post-content",
            "#article-content",
            ".story-content",
            ".article-body"
        ])
    elif "mashable.com" in url:
        selectors.extend([
            ".article-content",
            "#article-content",
            ".story-content",
            ".article-body"
        ])
    elif "venturebeat.com" in url:
        selectors.extend([
            ".article-content",
            "#article-content",
            ".story-content",
            ".post-content"
        ])
    elif "zdnet.com" in url:
        selectors.extend([
            ".storyBody",
            "#article-content",
            ".story-content",
            ".article-body"
        ])
    elif "cnet.com" in url:
        selectors.extend([
            ".article-main-body",
            "#article-content",
            ".story-content",
            ".article-body"
        ])
    elif "9to5mac.com" in url or "9to5google.com" in url:
        selectors.extend([
            ".post-content",
            "#article-content",
            ".story-content",
            ".article-body"
        ])
    elif "macrumors.com" in url:
        selectors.extend([
            ".article-content",
            "#article-content",
            ".story-content",
            ".post-content"
        ])
    elif "androidcentral.com" in url:
        selectors.extend([
            ".article-body",
            "#article-content",
            ".story-content",
            ".post-content"
        ])
    elif "imore.com" in url:
        selectors.extend([
            ".article-body",
            "#article-content",
            ".story-content",
            ".post-content"
        ])
    
    # Regional/Other International Sites
    elif "aljazeera.com" in url:
        selectors.extend([
            ".wysiwyg",
            "#article-content",
            ".story-content",
            ".article-body"
        ])
    elif "rt.com" in url:
        selectors.extend([
            ".article__text",
            "#article-content",
            ".story-content",
            ".article-body"
        ])
    elif "dw.com" in url:
        selectors.extend([
            ".longText",
            "#article-content",
            ".story-content",
            ".article-body"
        ])
    elif "france24.com" in url:
        selectors.extend([
            ".article-body",
            "#article-content",
            ".story-content",
            ".main-content"
        ])
    elif "euronews.com" in url:
        selectors.extend([
            ".article-body",
            "#article-content",
            ".story-content",
            ".main-content"
        ])
    elif "scmp.com" in url:
        selectors.extend([
            ".article-body",
            "#article-content",
            ".story-content",
            ".main-content"
        ])
    elif "japantimes.co.jp" in url:
        selectors.extend([
            ".article-body",
            "#article-content",
            ".story-content",
            ".main-content"
        ])
    elif "straitstimes.com" in url:
        selectors.extend([
            ".story-content",
            "#article-content",
            ".article-body",
            ".main-content"
        ])
    elif "thestar.com.my" in url:
        selectors.extend([
            ".story-content",
            "#article-content",
            ".article-body",
            ".main-content"
        ])
    elif "dawn.com" in url:
        selectors.extend([
            ".story__content",
            "#article-content",
            ".story-content",
            ".article-body"
        ])
    elif "thenews.com.pk" in url:
        selectors.extend([
            ".story-content",
            "#article-content",
            ".article-body",
            ".main-content"
        ])
    elif "dailystar.com.lb" in url:
        selectors.extend([
            ".story-content",
            "#article-content",
            ".article-body",
            ".main-content"
        ])
    elif "arabnews.com" in url:
        selectors.extend([
            ".article-content",
            "#article-content",
            ".story-content",
            ".main-content"
        ])
    
    return selectors

def get_site_specific_title_selectors(url: str) -> List[str]:
    """Get site-specific title selectors based on the URL"""
    selectors = []
    
    # Indian News Sites
    if "hindustantimes.com" in url:
        selectors.extend([".headline", ".story-headline", ".main-heading"])
    elif "timesofindia.indiatimes.com" in url:
        selectors.extend([".HNMDR", "._2ssWP", ".headline"])
    elif "indianexpress.com" in url:
        selectors.extend([".native_story_title", ".story-title", ".headline"])
    elif "ndtv.com" in url:
        selectors.extend([".sp-ttl", ".story__headline", ".headline"])
    elif "news18.com" in url:
        selectors.extend([".article-heading", ".story-headline"])
    elif "thehindu.com" in url:
        selectors.extend([".title", ".story-headline", ".article-headline"])
    elif "economictimes.indiatimes.com" in url:
        selectors.extend([".artTitle", ".headline", "h1.title"])
    elif "livemint.com" in url:
        selectors.extend([".headline", ".story-headline", ".main-title"])
    elif "businesstoday.in" in url:
        selectors.extend([".story-headline", ".headline", ".main-title"])
    elif "financialexpress.com" in url:
        selectors.extend([".story-headline", ".headline", ".main-title"])
    elif "moneycontrol.com" in url:
        selectors.extend([".article_title", ".headline", ".main-title"])
    elif "business-standard.com" in url:
        selectors.extend([".story-headline", ".headline", ".main-title"])
    elif "scroll.in" in url:
        selectors.extend([".story-headline", ".headline", ".main-title"])
    elif "thewire.in" in url:
        selectors.extend([".td-post-title", ".headline", ".main-title"])
    elif "newslaundry.com" in url:
        selectors.extend([".story-headline", ".headline", ".main-title"])
    elif "caravanmagazine.in" in url:
        selectors.extend([".story-headline", ".headline", ".main-title"])
    elif "outlookindia.com" in url:
        selectors.extend([".story-headline", ".headline", ".main-title"])
    elif "india.com" in url:
        selectors.extend([".story-headline", ".headline", ".main-title"])
    elif "firstpost.com" in url:
        selectors.extend([".story-headline", ".headline", ".main-title"])
    elif "news.abplive.com" in url:
        selectors.extend([".story-headline", ".headline", ".main-title"])
    elif "aajtak.in" in url:
        selectors.extend([".story-headline", ".headline", ".main-title"])
    elif "republicworld.com" in url:
        selectors.extend([".story-headline", ".headline", ".main-title"])
    elif "timesnownews.com" in url:
        selectors.extend([".story-headline", ".headline", ".main-title"])
    
    # International News Sites  
    elif "cnn.com" in url:
        selectors.extend([".headline__text", ".pg-headline", ".cd__headline"])
    elif "bbc.com" in url or "bbc.co.uk" in url:
        selectors.extend([".story-headline", ".gel-trafalgar-bold", "#main-heading"])
    elif "reuters.com" in url:
        selectors.extend([".ArticleHeader_headline", "[data-testid='Headline']"])
    elif "nytimes.com" in url:
        selectors.extend([".css-fwqvlz", "[data-testid='headline']", ".story-headline"])
    elif "washingtonpost.com" in url:
        selectors.extend([".headline", "[data-qa='headline']", ".article-headline"])
    elif "wsj.com" in url:
        selectors.extend([".wsj-article-headline", ".headline", ".article-headline"])
    elif "bloomberg.com" in url:
        selectors.extend([".lede-text-only__headline", "[data-module='Headline']"])
    elif "guardian.com" in url or "theguardian.com" in url:
        selectors.extend([".content__headline", ".headline", ".article-headline"])
    elif "independent.co.uk" in url:
        selectors.extend([".sc-1effbv5-0", ".headline", ".article-headline"])
    elif "telegraph.co.uk" in url:
        selectors.extend([".headline", ".article-headline", ".story-headline"])
    elif "ap.org" in url or "apnews.com" in url:
        selectors.extend([".Component-headline-0-2-89", ".headline", ".article-headline"])
    elif "npr.org" in url:
        selectors.extend([".storytitle", ".headline", ".article-headline"])
    elif "foxnews.com" in url:
        selectors.extend([".headline", ".article-headline", ".story-headline"])
    elif "nbcnews.com" in url:
        selectors.extend([".articleTitle", ".headline", ".article-headline"])
    elif "cbsnews.com" in url:
        selectors.extend([".content__title", ".headline", ".article-headline"])
    elif "abcnews.go.com" in url:
        selectors.extend([".Article__Headline", ".headline", ".article-headline"])
    elif "usatoday.com" in url:
        selectors.extend([".asset-headline", ".headline", ".article-headline"])
    elif "politico.com" in url:
        selectors.extend([".headline", ".article-headline", ".story-headline"])
    elif "huffpost.com" in url or "huffingtonpost.com" in url:
        selectors.extend([".headline__text", ".headline", ".article-headline"])
    elif "axios.com" in url:
        selectors.extend([".gtm-story-headline", ".headline", ".article-headline"])
    elif "vox.com" in url:
        selectors.extend([".c-page-title", ".headline", ".article-headline"])
    elif "buzzfeednews.com" in url:
        selectors.extend([".news-article-header__title", ".headline", ".article-headline"])
    elif "vice.com" in url:
        selectors.extend([".article__title", ".headline", ".article-headline"])
    elif "slate.com" in url:
        selectors.extend([".article__hed", ".headline", ".article-headline"])
    elif "theatlantic.com" in url:
        selectors.extend([".article-header__title", ".headline", ".article-headline"])
    elif "newyorker.com" in url:
        selectors.extend([".ArticleHeader__hed", ".headline", ".article-headline"])
    elif "time.com" in url:
        selectors.extend([".headline", ".article-headline", ".story-headline"])
    elif "newsweek.com" in url:
        selectors.extend([".title", ".headline", ".article-headline"])
    elif "fortune.com" in url:
        selectors.extend([".article-headline", ".headline", ".story-headline"])
    elif "forbes.com" in url:
        selectors.extend([".article-headline", ".headline", ".story-headline"])
    elif "businessinsider.com" in url:
        selectors.extend([".post-headline", ".headline", ".article-headline"])
    elif "techcrunch.com" in url:
        selectors.extend([".article__title", ".headline", ".entry-title"])
    elif "theverge.com" in url:
        selectors.extend([".c-page-title", ".headline", ".article-headline"])
    elif "wired.com" in url:
        selectors.extend([".ContentHeaderHed", ".headline", ".article-headline"])
    elif "arstechnica.com" in url:
        selectors.extend([".article-title", ".headline", ".post-title"])
    elif "engadget.com" in url:
        selectors.extend([".article-title", ".headline", ".story-headline"])
    elif "gizmodo.com" in url:
        selectors.extend([".headline", ".post-title", ".article-headline"])
    elif "mashable.com" in url:
        selectors.extend([".article-title", ".headline", ".story-headline"])
    elif "venturebeat.com" in url:
        selectors.extend([".article-title", ".headline", ".post-title"])
    elif "zdnet.com" in url:
        selectors.extend([".storyTitle", ".headline", ".article-headline"])
    elif "cnet.com" in url:
        selectors.extend([".article-headline", ".headline", ".story-headline"])
    elif "9to5mac.com" in url or "9to5google.com" in url:
        selectors.extend([".post-title", ".headline", ".article-headline"])
    elif "macrumors.com" in url:
        selectors.extend([".article-title", ".headline", ".post-title"])
    elif "androidcentral.com" in url:
        selectors.extend([".article-title", ".headline", ".post-title"])
    elif "imore.com" in url:
        selectors.extend([".article-title", ".headline", ".post-title"])
    elif "aljazeera.com" in url:
        selectors.extend([".article-heading", ".headline", ".story-headline"])
    elif "rt.com" in url:
        selectors.extend([".article__heading", ".headline", ".story-headline"])
    elif "dw.com" in url:
        selectors.extend([".article-title", ".headline", ".story-headline"])
    elif "france24.com" in url:
        selectors.extend([".article-title", ".headline", ".story-headline"])
    elif "euronews.com" in url:
        selectors.extend([".article-title", ".headline", ".story-headline"])
    elif "scmp.com" in url:
        selectors.extend([".article-title", ".headline", ".story-headline"])
    elif "japantimes.co.jp" in url:
        selectors.extend([".article-title", ".headline", ".story-headline"])
    elif "straitstimes.com" in url:
        selectors.extend([".story-headline", ".headline", ".article-title"])
    elif "thestar.com.my" in url:
        selectors.extend([".story-headline", ".headline", ".article-title"])
    elif "dawn.com" in url:
        selectors.extend([".story__title", ".headline", ".story-headline"])
    elif "thenews.com.pk" in url:
        selectors.extend([".story-headline", ".headline", ".article-title"])
    elif "dailystar.com.lb" in url:
        selectors.extend([".story-headline", ".headline", ".article-title"])
    elif "arabnews.com" in url:
        selectors.extend([".article-title", ".headline", ".story-headline"])
    
    return selectors

def clean_title_suffix(title: str) -> str:
    """
    Clean common suffixes from titles
    """
    if not title:
        return title
    
    # Common suffixes to remove
    suffixes = [
        ' - NDTV', ' | NDTV', ' - NDTV.com', ' | NDTV.com',
        ' - News', ' | News', ' - Latest News', ' | Latest News',
        ' - Breaking News', ' | Breaking News',
        ' - Video', ' | Video', ' - Videos', ' | Videos',
        ' - Watch', ' | Watch'
    ]
    
    for suffix in suffixes:
        if title.endswith(suffix):
            title = title[:-len(suffix)].strip()
            break
    
    return title

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
        
        # HANDLE GOOGLE NEWS REDIRECTS - Enhanced approach
        if "news.google.com" in url or "news.google.com" in current_url:
            logger.info("🔄 Detected Google News URL, attempting to resolve to actual article...")
            try:
                # Method 1: Try to decode the Google News URL directly
                import urllib.parse
                
                # Extract the actual URL from Google News redirect
                if "articles/" in url:
                    # Try to find the actual URL in the redirect
                    try:
                        # Wait a bit longer for potential redirects
                        await page.wait_for_timeout(3000)
                        
                        # Check if we were redirected to the actual article
                        final_url = page.url
                        if "news.google.com" not in final_url:
                            current_url = final_url
                            logger.info(f"✅ Auto-redirected to: {current_url}")
                        else:
                            # Method 2: Try to find article links on the page
                            logger.info("🔍 Searching for article links on Google News page...")
                            
                            # More comprehensive selectors for Google News
                            selectors_to_try = [
                                "a[href*='http']:not([href*='google.com']):not([href*='youtube.com'])",
                                "article a",
                                "[data-n-tid] a",
                                "h3 a",
                                "h4 a", 
                                ".article a",
                                ".story a",
                                "[role='article'] a"
                            ]
                            
                            article_links = []
                            for selector in selectors_to_try:
                                try:
                                    elements = await page.query_selector_all(selector)
                                    if elements:
                                        logger.info(f"🔍 Found {len(elements)} links with selector: {selector}")
                                        for element in elements[:15]:  # Check more links
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
                                logger.info(f"✅ Successfully redirected to: {current_url}")
                            else:
                                logger.warning("❌ Could not find valid article links on Google News page")
                                # Return early with error for Google News URLs that can't be resolved
                                return {
                                    "resolved_url": url,
                                    "image_url": "https://via.placeholder.com/300x150?text=Google+News+Redirect+Failed",
                                    "title": "Google News Redirect Failed",
                                    "description": "Could not resolve Google News URL to actual article",
                                    "error": "Google News redirect failed"
                                }
                    except Exception as e:
                        logger.warning(f"❌ Error resolving Google News URL: {e}")
                        return {
                            "resolved_url": url,
                            "image_url": "https://via.placeholder.com/300x150?text=Google+News+Error",
                            "title": "Google News Processing Error", 
                            "description": f"Error processing Google News URL: {str(e)}",
                            "error": f"Google News error: {str(e)}"
                        }
                        
            except Exception as e:
                logger.warning(f"❌ Error handling Google News redirect: {e}")
                return {
                    "resolved_url": url,
                    "image_url": "https://via.placeholder.com/300x150?text=Redirect+Error",
                    "title": "Redirect Error",
                    "description": f"Failed to handle redirect: {str(e)}",
                    "error": f"Redirect error: {str(e)}"
                }
        
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
        page_title = await page.title()
        
        # Extract a clean article title using multiple strategies
        clean_title = await extract_clean_title(page, page_title)
        
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
                    
                    # Get dimensions
                    try:
                        w = int(width) if width else 0
                        h = int(height) if height else 0
                        area = w * h if w and h else 0
                    except (ValueError, TypeError):
                        area = 0
                    
                    image_candidates.append({
                        'src': src,
                        'area': area,
                        'alt': alt_text,
                        'width': w,
                        'height': h
                    })
                    
                except Exception as e:
                    continue
            
            # Sort by area (larger images generally better)
            image_candidates.sort(key=lambda x: x['area'], reverse=True)
            
            # Find the best valid image
            for candidate in image_candidates:
                if is_valid_news_image(candidate):
                    best_image = candidate['src']
                    logger.info(f"Selected image: {candidate['src'][:50]}...")
                    break
                    
        except Exception as e:
            logger.debug(f"Error in enhanced image extraction: {e}")
        
        # Choose the best image with fallback hierarchy
        image_url = og_image or twitter_image or best_image
        
        # Extract clean article content (not the entire page)
        description = await extract_clean_article_content(page)
        
        return {
            "resolved_url": current_url,
            "image_url": image_url,
            "title": clean_title,  # Use the clean title
            "description": description
        }
    except Exception as e:
        logger.error(f"Error extracting article details from {url}: {e}")
        logger.error(traceback.format_exc())
        return {
            "resolved_url": None,
            "image_url": "https://via.placeholder.com/300x150?text=No+Image",
            "title": None,
            "description": None,
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
        
        # Filter and prioritize sentences (no scoring)
        filtered_sentences = []
        for sentence in sentences:
            if len(sentence.split()) < 5:  # Skip very short sentences
                continue
                
            sentence_lower = sentence.lower()
            
            # Prioritize sentences with Indian context
            has_indian_context = any(keyword in sentence_lower for keyword in indian_context_keywords)
            
            # Prioritize sentences with numbers/dates (often important facts)
            import re
            has_numbers = bool(re.search(r'\d+', sentence))
            
            # Prioritize sentences with proper nouns (names, places)
            words = sentence.split()
            proper_nouns = sum(1 for word in words if word[0].isupper() and len(word) > 2)
            has_proper_nouns = proper_nouns > 0
            
            # Calculate priority (higher is better)
            priority = 0
            if has_indian_context:
                priority += 3
            if has_numbers:
                priority += 2
            if has_proper_nouns:
                priority += 1
            
            # Prefer sentences from early in the text
            position_bonus = max(0, 3 - (sentences.index(sentence) // 3))
            priority += position_bonus
            
            filtered_sentences.append((sentence, priority))
        
        # Sort by priority (highest first)
        filtered_sentences.sort(key=lambda x: x[1], reverse=True)
        
        # Build summary from highest-priority sentences
        summary = ""
        word_count = 0
        used_sentences = []
        
        for sentence, priority in filtered_sentences:
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
                for i, (original_sentence, _) in enumerate(filtered_sentences):
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
        # Don't truncate the original text, return it as-is
        return text or "No content available for summarization."

async def process_single_article_playwright(article: Dict, page, timeout: int) -> Dict:
    """Process a single article using Playwright"""
    try:
        input_title = article.get('title', 'Unknown Title')
        url = article.get('link')
        source = article.get('source', 'Unknown Source')
        published = article.get('published', '')
        
        if not url:
            return {
                'id': 'no-url',
                'title': input_title,
                'source': source,
                'url': '',
                'image_url': 'https://via.placeholder.com/300x150?text=No+URL',
                'published': published,
                'error': 'No URL provided'
            }
        
        logger.debug(f"🔄 Processing: {input_title[:50]}... - {source}")
        
        # Extract article details using Playwright
        article_details = await extract_article_details_playwright(url, page, timeout)
        
        # Use the extracted title from the page, falling back to input title if needed
        final_title = article_details['title'] or input_title
        
        # Generate a unique ID for the article
        article_id = generate_article_id(url, final_title, source)
        
        # Quality scoring removed - no longer needed
        
        # Generate content hash for duplicate detection
        content_hash = hashlib.md5(article_details['description'][:200].encode()).hexdigest() if article_details['description'] else None
        
        # Generate key points from the description
        key_points = generate_key_points(article_details['description'], final_title) if article_details['description'] else []
        
        # Create Inshorts-style article with content hash and key points
        processed_article = {
            'id': article_id,
            'title': final_title,  # Use the clean title extracted from the page
            'source': source,
            'url': article_details['resolved_url'] or url,
            'image_url': article_details['image_url'],
            'description': article_details['description'],
            'key_points': key_points,  # Add key points
            'published': published,
            'content_hash': content_hash
        }
        
        return processed_article
        
    except Exception as e:
        logger.error(f"Error processing article {input_title[:50]}...: {e}")
        return {
            'id': 'error',
            'title': input_title,
            'source': source,
            'url': url or '',
            'image_url': 'https://via.placeholder.com/300x150?text=Error',
            'published': published,
            'error': str(e)
        }

async def process_news_data_playwright(news_data: Dict, max_articles: int, timeout: int, headless: bool) -> List[Dict]:
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
                
                result = await process_single_article_playwright(article, page, timeout)
                
                # Check for duplicate content before adding
                if 'error' not in result and result.get('description'):
                    if is_duplicate_content(result['description'], processed_articles):
                        logger.info(f"🔄 Skipping duplicate content: {result['title'][:50]}...")
                        continue
                
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

# Image quality scoring removed - no longer needed

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
    
    # Basic validation passed
    
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

# Content quality scoring removed - no longer needed

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