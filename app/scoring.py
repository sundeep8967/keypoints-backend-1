"""
Scoring utilities for news articles - extracted from generate_inshorts_playwright.py
"""
import re
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

def calculate_image_quality_score(src: str, alt_text: str, width: str, height: str, class_name: str) -> int:
    """Calculate quality score for an image based on multiple factors"""
    score = 0
    
    # Check image dimensions
    try:
        w = int(width) if width and width.isdigit() else 0
        h = int(height) if height and height.isdigit() else 0
        
        # Prefer larger images (but not too large)
        if w >= 300 and h >= 200:
            score += 20
    except:
        pass
    
    # Check if it's likely a content image (not icon/logo)
    if alt_text:
        score += 30
    
    # Penalize small images or icons
    if any(keyword in src.lower() for keyword in ['icon', 'logo', 'avatar', 'thumb']):
        if any(keyword in src.lower() for keyword in ['icon', 'logo']):
            score -= 50
    
    # Boost for high-quality image sources
    if any(domain in src.lower() for domain in ['cdn', 'img', 'images', 'static']):
        if 'cdn' in src.lower():
            score += 40
        else:
            score += 20
        if 'thumb' in src.lower():
            score -= 30
    
    # Check class names for content indicators
    if class_name:
        content_indicators = ['article', 'content', 'main', 'featured', 'hero']
        if any(indicator in class_name.lower() for indicator in content_indicators):
            score += 15
    
    # Return score (minimum 0)
    return max(0, score)


def calculate_content_quality_score(title: str, image_url: str, description: str, source: str) -> float:
    """
    Calculate a quality score for the article content (0-1000).
    
    Factors considered:
    - Breaking news keywords (highest priority)
    - Political content relevance
    - Social/trending topics
    - Content length and quality
    - Image availability and quality
    - Source credibility
    - Regional relevance (Indian context)
    
    Returns:
        Quality score between 0-1000
    """
    score = 0.0
    
    # Combine all text for analysis
    all_text = f"{title} {description}".lower()
    
    # Regional boost for Indian content
    regional_boost = 0
    indian_keywords = [
        'india', 'indian', 'delhi', 'mumbai', 'bengaluru', 'bangalore', 'chennai',
        'hyderabad', 'pune', 'kolkata', 'ahmedabad', 'surat', 'jaipur', 'lucknow',
        'kanpur', 'nagpur', 'indore', 'thane', 'bhopal', 'visakhapatnam', 'pimpri',
        'patna', 'vadodara', 'ludhiana', 'agra', 'nashik', 'faridabad', 'meerut',
        'rajkot', 'kalyan', 'vasai', 'varanasi', 'srinagar', 'aurangabad', 'dhanbad',
        'amritsar', 'navi mumbai', 'allahabad', 'ranchi', 'howrah', 'coimbatore',
        'jabalpur', 'gwalior', 'vijayawada', 'jodhpur', 'madurai', 'raipur', 'kota',
        'guwahati', 'chandigarh', 'modi', 'bjp', 'congress', 'parliament', 'lok sabha',
        'rajya sabha', 'supreme court', 'high court', 'cbi', 'ed', 'rbi', 'sebi',
        'isro', 'drdo', 'iit', 'iim', 'upsc', 'neet', 'jee', 'cbse', 'icse',
        'bollywood', 'tollywood', 'kollywood', 'ipl', 'bcci', 'cricket', 'hockey',
        'kabaddi', 'badminton', 'wrestling', 'boxing', 'shooting', 'archery',
        'rupee', 'nse', 'bse', 'sensex', 'nifty', 'lic', 'sbi', 'hdfc', 'icici',
        'tata', 'reliance', 'adani', 'ambani', 'ratan tata', 'mukesh ambani'
    ]
    
    for keyword in indian_keywords:
        if keyword in all_text:
            regional_boost = 50
            break
    
    # Breaking news detection (highest priority)
    breaking_score = 0
    breaking_keywords = ['breaking', 'urgent', 'alert', 'live', 'developing', 'just in', 'flash']
    for keyword in breaking_keywords:
        if keyword in all_text:
            breaking_score = 900  # Very high priority
            break
    
    # Political content scoring
    political_score = 0
    political_keywords = ['election', 'vote', 'government', 'minister', 'parliament', 'policy', 'law', 'court', 'judge']
    for keyword in political_keywords:
        if keyword in all_text:
            political_score = max(political_score, 700)
    
    # Social/trending content scoring
    social_score = 0
    social_keywords = ['viral', 'trending', 'social media', 'twitter', 'facebook', 'instagram', 'youtube']
    for keyword in social_keywords:
        if keyword in all_text:
            social_score = max(social_score, 500)
    
    # Source credibility multiplier
    source_multiplier = 1.0
    trusted_sources = ['bbc', 'reuters', 'ap', 'ndtv', 'times of india', 'hindu', 'indian express', 'hindustan times']
    if any(trusted_source in source.lower() for trusted_source in trusted_sources):
        source_multiplier = 1.2
    
    # Base content quality scoring
    base_score = 0
    
    # Title quality
    if title:
        if len(title) > 50:
            base_score += 80
        elif len(title) > 30:
            base_score += 60
        else:
            base_score += 20
    
    # Description quality
    if description:
        if len(description) > 500:
            base_score += 120
        elif len(description) > 200:
            base_score += 80
        else:
            base_score += 40
    
    # Image quality
    if image_url:
        if 'cdn' in image_url.lower():
            base_score += 60  # Likely a proper image CDN
        else:
            base_score += 40
    
    # Content freshness and relevance
    if any(word in all_text for word in ['today', 'yesterday', 'latest', 'new', 'recent']):
        base_score += 40
    if any(word in all_text for word in ['update', 'report', 'announce', 'reveal']):
        base_score += 20
    
    # Calculate final score
    # Priority: breaking > political > social, then add base score and regional boost
    importance_score = max(breaking_score, political_score, social_score)
    final_score = (importance_score + base_score + regional_boost) * source_multiplier
    
    return min(final_score, 1000.0)


def score_sentences_for_summary(sentences: List[str], title: str = "") -> List[Tuple[str, int]]:
    """
    Score sentences for extractive summarization.
    
    Args:
        sentences: List of sentences to score
        title: Article title for context
        
    Returns:
        List of (sentence, score) tuples sorted by score
    """
    scored_sentences = []
    title_lower = title.lower() if title else ""
    
    for i, sentence in enumerate(sentences):
        sentence_lower = sentence.lower()
        score = 0
        
        # Boost score for Indian context
        indian_keywords = ['india', 'indian', 'delhi', 'mumbai', 'bengaluru', 'bangalore']
        for keyword in indian_keywords:
            if keyword in sentence_lower:
                score += 10
        
        # Boost score for sentences with numbers/dates (often important facts)
        if re.search(r'\d+', sentence):
            score += 5
        
        # Boost score for sentences with proper nouns (names, places)
        proper_nouns = len(re.findall(r'\b[A-Z][a-z]+\b', sentence))
        score += proper_nouns * 2
        
        # Position bonus (earlier sentences often more important)
        position_bonus = max(0, 10 - i)
        score += position_bonus
        
        scored_sentences.append((sentence, score))
    
    # Sort by score (highest first)
    scored_sentences.sort(key=lambda x: x[1], reverse=True)
    
    return scored_sentences