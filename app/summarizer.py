"""
Text summarization service for news articles.
"""
import logging
import nltk
import time
import traceback
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
    def summarize_from_url(url: str, max_sentences: int = 3, timeout: int = 20) -> Optional[str]:
        """
        Summarize a news article from its URL.
        
        Args:
            url: URL of the news article
            max_sentences: Maximum number of sentences in the summary
            timeout: Timeout in seconds for article download
            
        Returns:
            Summarized text or None if summarization fails
        """
        try:
            # Handle Google News redirects
            if "news.google.com" in url:
                logger.info(f"Detected Google News URL: {url}")
                # For Google News URLs, we need to extract the actual article URL
                # This is a simplified approach - might need adjustment based on URL format
                if "articles" in url and "?" in url:
                    url = url.split("?")[0]
                    logger.info(f"Modified Google News URL: {url}")
            
            # Check if URL is valid
            if not url.startswith(('http://', 'https://')):
                logger.warning(f"Invalid URL format: {url}")
                return None
                
            logger.info(f"Downloading article from: {url}")
            start_time = time.time()
            
            # Download and parse the article with timeout
            article = Article(url)
            article.download()
            
            # Check timeout after download
            if time.time() - start_time > timeout:
                logger.warning(f"Timeout downloading article from {url}")
                return None
                
            article.parse()
            
            # If article has built-in summarization, use it
            try:
                article.nlp()
                if article.summary:
                    logger.info(f"Generated summary for {url} using newspaper3k (length: {len(article.summary)})")
                    return article.summary
            except Exception as e:
                logger.warning(f"NLP summarization failed, falling back to extractive: {e}")
                
            # Fall back to extractive summarization if needed
            return NewsSummarizer.extractive_summarize(article.text, max_sentences)
            
        except ArticleException as e:
            logger.error(f"Article exception for {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error summarizing article from {url}: {e}")
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
            if not text or len(text.strip()) < 10:
                logger.warning("Text too short to summarize")
                return None
                
            # Tokenize the text into sentences
            sentences = sent_tokenize(text)
            
            if not sentences:
                logger.warning("No sentences found in text")
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
            if not summary:
                logger.warning("Empty summary provided")
                return ""
                
            # Remove the title from the summary if it appears there
            if title and summary.startswith(title):
                summary = summary[len(title):].strip()
                
            # Split into sentences
            sentences = sent_tokenize(summary)
            
            if not sentences:
                logger.warning("No sentences found in summary")
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