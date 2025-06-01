"""
Text summarization service for news articles.
"""
import logging
import nltk
import time
import traceback
import requests
import base64
import re
from typing import Optional
from newspaper import Article, ArticleException
from nltk.tokenize import sent_tokenize

# Download necessary NLTK data
try:
    nltk.download('punkt', quiet=True)
    logging.info("NLTK punkt downloaded successfully")
except Exception as e:
    logging.error(f"Failed to download NLTK data: {e}")
    pass  # Handle silently if download fails

logger = logging.getLogger(__name__)

class NewsSummarizer:
    """Service for summarizing news articles."""
    
    @staticmethod
    def _decode_google_news_url(url: str) -> Optional[str]:
        """
        Decodes Google News CBM URLs to extract the actual article URL.
        Google News URLs often embed the original URL in a base64-encoded string.
        Example: https://news.google.com/rss/articles/CBMibkFVX3lxTE1aU2h5ZV9aZFRsU3VxT0lLTXdFVk9xb09mRFZNVDkyanMtVnNGczBWRDltSVFzMVRsekw1djM1WEhtOFJhak82eXdNY2VNV1p3ZjBLNi1GbGhDREd5YmlycnBGcHU4VU9zWDQ5Z1Bn?oc=5
        """
        try:
            # Regex to capture the Base64 encoded part between 'CBM' and the end of the string
            # It should capture URL-safe Base64 characters (A-Z, a-z, 0-9, -, _)
            match = re.search(r'CBM([A-Za-z0-9_-]+)', url)
            if not match:
                logger.warning(f"No CBM part found in Google News URL: {url}")
                return None

            encoded_part = match.group(1)
            
            # urlsafe_b64decode handles '-' and '_' automatically, but needs correct padding
            padding_needed = len(encoded_part) % 4
            if padding_needed != 0:
                encoded_part += '=' * (4 - padding_needed)

            decoded_bytes = base64.urlsafe_b64decode(encoded_part)
            decoded_string = decoded_bytes.decode('utf-8', errors='ignore')

            # Extract the first valid URL from the decoded string
            urls_found = re.findall(r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+\S*', decoded_string)

            if urls_found:
                # Prioritize a non-Google News URL if multiple are found
                for found_url in urls_found:
                    if "news.google.com" not in found_url:
                        return found_url
                return urls_found[0] # Fallback to the first found URL if all are Google News
            
            logger.warning(f"Could not extract a valid URL from decoded Google News string: {decoded_string}")
            return None
        except Exception as e:
            logger.error(f"Error decoding Google News URL {url}: {e}")
            logger.error(traceback.format_exc())
            return None

    @staticmethod
    def summarize_from_url(url: str, max_sentences: int = 3, timeout: int = 20) -> Optional[dict]:
        """
        Summarize a news article from its URL and extract additional content.
        
        Args:
            url: URL of the news article
            max_sentences: Maximum number of sentences in the summary
            timeout: Timeout in seconds for article download
            
        Returns:
            Dictionary with summary, top_image, and other metadata
        """
        try:
            resolved_url = url

            # Try to decode Google News CBM URL first
            if "news.google.com" in url:
                logger.info(f"Detected Google News URL: {url}, attempting to decode...")
                decoded = NewsSummarizer._decode_google_news_url(url)
                if decoded:
                    resolved_url = decoded
                    logger.info(f"Decoded to: {resolved_url}")
                else:
                    logger.warning(f"Could not decode Google News URL: {url}")
            
            # Always try to follow redirects, even if it's not a Google News URL or decoding failed
            try:
                # Use a proper User-Agent to avoid being blocked
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
                response = requests.get(resolved_url, allow_redirects=True, timeout=5, headers=headers)
                if response.url != resolved_url:
                    logger.info(f"Followed redirect from {resolved_url} to {response.url}")
                    resolved_url = response.url
                response.raise_for_status() # Raise an exception for HTTP errors
            except requests.exceptions.RequestException as e:
                logger.warning(f"Could not follow redirect or fetch content for {resolved_url}: {e}")
                return None

            # Check if resolved URL is valid
            if not resolved_url or not resolved_url.startswith(('http://', 'https://')):
                logger.warning(f"Invalid URL format after resolution: {resolved_url}")
                return None
                
            logger.info(f"Downloading article from: {resolved_url}")
            start_time = time.time()
            
            # Download and parse the article with timeout
            article = Article(resolved_url, fetch_images=True)
            article.download()
            
            # Check timeout after download
            if time.time() - start_time > timeout:
                logger.warning(f"Timeout downloading article from {resolved_url}")
                return None
                
            article.parse()
            
            # Extract images and metadata
            result = {
                'summary': None,
                'top_image': article.top_image,
                'images': list(article.images)[:5] if article.images else [],
                'title': article.title,
                'authors': article.authors,
                'publish_date': article.publish_date,
                'text': article.text
            }
            
            # Generate summary
            try:
                article.nlp()
                if article.summary:
                    logger.info(f"Generated summary for {resolved_url} using newspaper3k (length: {len(article.summary)}). Article text length: {len(article.text)}")
                    result['summary'] = article.summary
                else:
                    # Fall back to extractive summarization if needed
                    logger.warning(f"Newspaper3k NLP summary empty, falling back to extractive. Article text length: {len(article.text)}")
                    result['summary'] = NewsSummarizer.extractive_summarize(article.text, max_sentences)
            except Exception as e:
                logger.warning(f"NLP summarization failed, falling back to extractive: {e}. Article text length: {len(article.text)}")
                result['summary'] = NewsSummarizer.extractive_summarize(article.text, max_sentences)
            
            # If summary is still short after fallback, check text length
            if not result['summary'] or len(result['summary'].strip()) < 50:
                logger.warning(f"Summary still too short after processing for {resolved_url}. Final article text length: {len(article.text)}")
                if len(article.text) > 200:
                    result['summary'] = NewsSummarizer.extractive_summarize(article.text, max_sentences)
                else:
                    result['summary'] = article.text[:max_sentences*60] # Just take a snippet of text if all else fails

            # Ensure text excerpt is not too long
            result['text'] = result['text'][:1000] + '...' if len(result['text']) > 1000 else result['text']
                
            logger.info(f"Successfully extracted article data: title='{result['title']}', top_image={bool(result['top_image'])}, summary_length={len(result['summary']) if result['summary'] else 0}")
            return result
            
        except ArticleException as e:
            logger.error(f"Article exception for {resolved_url}: {e}")
            logger.error(traceback.format_exc())
            return None
        except Exception as e:
            logger.error(f"Unhandled error summarizing article from {resolved_url}: {e}")
            logger.error(traceback.format_exc())
            return None
    
    @staticmethod
    def extractive_summarize(text: str, max_sentences: int = 3) -> Optional[str]:
        """
        Create an extractive summary of text by selecting important sentences.
        
        Args:
            text: Text to summarize
            max_sentences: Maximum number of sentences in the summary
            
        Returns:
            Summarized text or None if summarization fails
        """
        try:
            if not text or len(text.strip()) < 50: # Increased minimum text length for summarization
                logger.warning(f"Text too short to summarize. Length: {len(text.strip())}")
                return None
                
            # Tokenize the text into sentences
            sentences = sent_tokenize(text)
            
            if not sentences:
                logger.warning("No sentences found in text for extractive summarization")
                return None
                
            # For a simple approach, just take the first few sentences
            # In a more advanced implementation, you'd use ranking algorithms
            summary_sentences = sentences[:max_sentences]
            
            # Join the sentences back into a summary
            summary = ' '.join(summary_sentences)
            
            logger.info(f"Generated extractive summary of {len(summary)} chars from {len(text)} chars of text")
            return summary
            
        except Exception as e:
            logger.error(f"Error in extractive summarization: {e}")
            logger.error(traceback.format_exc())
            return None
            
    @staticmethod
    def format_inshorts_style(title: str, summary: str, max_chars: int = 60) -> str:
        """
        Format a summary in Inshorts style (very concise).
        
        Args:
            title: Article title
            summary: Article summary
            max_chars: Target maximum characters per sentence
            
        Returns:
            Inshorts-style summary
        """
        try:
            if not summary or len(summary.strip()) < 10:
                logger.warning(f"Empty or very short summary provided for Inshorts style. Length: {len(summary.strip() if summary else '')}")
                return ""
                
            # Remove the title from the summary if it appears there
            if title and summary.startswith(title):
                summary = summary[len(title):].strip()
                
            # Split into sentences
            sentences = sent_tokenize(summary)
            
            if not sentences:
                logger.warning("No sentences found in summary for Inshorts style")
                return summary
                
            # Simplify sentences to target length
            short_sentences = []
            for sentence in sentences:
                if len(sentence) <= max_chars:
                    short_sentences.append(sentence)
                else:
                    # Simple truncation - a more sophisticated approach would use NLP
                    short_sentences.append(sentence[:max_chars-3] + '...')
                    
            # Limit to 3 sentences max for Inshorts style
            if len(short_sentences) > 3:
                short_sentences = short_sentences[:3]
                
            result = ' '.join(short_sentences)
            logger.info(f"Formatted Inshorts style summary: {len(result)} chars")
            return result
            
        except Exception as e:
            logger.error(f"Error formatting Inshorts style: {e}")
            logger.error(traceback.format_exc())
            return summary  # Return original summary on error 