"""
Text summarization service for news articles.
"""
import logging
import nltk
from typing import Optional
from newspaper import Article
from nltk.tokenize import sent_tokenize

# Download necessary NLTK data
try:
    nltk.download('punkt', quiet=True)
except:
    pass  # Handle silently if download fails

logger = logging.getLogger(__name__)

class NewsSummarizer:
    """Service for summarizing news articles."""
    
    @staticmethod
    def summarize_from_url(url: str, max_sentences: int = 3) -> Optional[str]:
        """
        Summarize a news article from its URL.
        
        Args:
            url: URL of the news article
            max_sentences: Maximum number of sentences in the summary
            
        Returns:
            Summarized text or None if summarization fails
        """
        try:
            # Download and parse the article
            article = Article(url)
            article.download()
            article.parse()
            
            # If article has built-in summarization, use it
            article.nlp()
            if article.summary:
                logger.info(f"Generated summary for {url} using newspaper3k")
                return article.summary
                
            # Fall back to extractive summarization if needed
            return NewsSummarizer.extractive_summarize(article.text, max_sentences)
            
        except Exception as e:
            logger.error(f"Error summarizing article from {url}: {e}")
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
            # Tokenize the text into sentences
            sentences = sent_tokenize(text)
            
            if not sentences:
                return None
                
            # For a simple approach, just take the first few sentences
            # In a more advanced implementation, you'd use ranking algorithms
            summary_sentences = sentences[:max_sentences]
            
            # Join the sentences back into a summary
            summary = ' '.join(summary_sentences)
            
            logger.info(f"Generated extractive summary of {len(summary)} chars")
            return summary
            
        except Exception as e:
            logger.error(f"Error in extractive summarization: {e}")
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
            # Remove the title from the summary if it appears there
            if summary.startswith(title):
                summary = summary[len(title):].strip()
                
            # Split into sentences
            sentences = sent_tokenize(summary)
            
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
                
            return ' '.join(short_sentences)
            
        except Exception as e:
            logger.error(f"Error formatting Inshorts style: {e}")
            return summary  # Return original summary on error 