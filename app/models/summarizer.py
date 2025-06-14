from transformers import pipeline, AutoModelForSequenceClassification, AutoTokenizer
import torch
import numpy as np
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from textblob import TextBlob
import nltk
from nltk.tokenize import sent_tokenize
import logging
import sys
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add path to ensure imports work correctly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Download necessary NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

class NLPProcessor:
    def __init__(self):
        self.summarizer = None
        self.sentiment_analyzer = None
        self.tokenizer = None
        self.model = None
        self.initialized = False
        
        # Initialize models
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize the NLP models"""
        try:
            # Initialize summarizer
            try:
                self.summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
                logger.info("Summarizer initialized successfully")
            except Exception as e:
                logger.error(f"Error initializing summarizer: {e}")
                self.summarizer = None
            
            # Initialize sentiment analysis
            try:
                model_name = "distilbert-base-uncased-finetuned-sst-2-english"
                self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
                self.tokenizer = AutoTokenizer.from_pretrained(model_name)
                self.sentiment_analyzer = pipeline("sentiment-analysis", model=model_name)
                logger.info("Sentiment analyzer initialized successfully")
            except Exception as e:
                logger.error(f"Error initializing sentiment analyzer: {e}")
                self.sentiment_analyzer = None
            
            # If at least one model is initialized, consider it a success
            self.initialized = (self.summarizer is not None) or (self.sentiment_analyzer is not None)
            
            if self.initialized:
                logger.info("NLP models partially or fully initialized")
            else:
                logger.warning("No NLP models were initialized, using fallback methods only")
                
        except Exception as e:
            logger.error(f"Error in NLP model initialization: {e}")
            self.initialized = False
    
    def summarize_text(self, text, max_length=150, min_length=30):
        """Generate a summary of the input text"""
        if self.initialized and self.summarizer:
            try:
                if len(text.split()) < min_length:
                    return text  # Text is already short enough
                
                summary = self.summarizer(text, max_length=max_length, min_length=min_length, do_sample=False)
                return summary[0]['summary_text']
            except Exception as e:
                logger.error(f"Error summarizing text with model: {e}")
                # Fall through to fallback method
        
        # Fallback: Extract first few sentences as summary
        return self._extract_summary_fallback(text, max_length)
    
    def _extract_summary_fallback(self, text, max_length=150):
        """Fallback method to extract summary when model is not available"""
        try:
            sentences = sent_tokenize(text)
            
            if len(sentences) <= 2:
                return text
            
            # Use first 2-3 sentences as summary
            summary_sentences = sentences[:min(3, len(sentences))]
            summary = ' '.join(summary_sentences)
            
            # Truncate if still too long
            if len(summary) > max_length * 2:  # Allow twice the max_length for fallback
                summary = summary[:max_length * 2] + '...'
                
            return summary
        except Exception as e:
            logger.error(f"Error in fallback summary extraction: {e}")
            # Last resort fallback
            return text[:100] + "..."
    
    def analyze_sentiment(self, text):
        """Analyze the sentiment of the input text"""
        if self.initialized and self.sentiment_analyzer:
            try:
                # For longer texts, analyze each sentence and average the results
                if len(text.split()) > 100:
                    sentences = sent_tokenize(text)
                    sentiments = self.sentiment_analyzer(sentences)
                    
                    # Calculate weighted average based on sentence length
                    total_score = 0
                    total_weight = 0
                    
                    for sent, sentiment in zip(sentences, sentiments):
                        weight = len(sent.split())
                        score = 1 if sentiment['label'] == 'POSITIVE' else 0
                        total_score += score * weight
                        total_weight += weight
                    
                    avg_sentiment = total_score / total_weight if total_weight > 0 else 0.5
                    
                    # Map to emotional categories
                    return self._map_sentiment_to_emotion(avg_sentiment)
                else:
                    # For shorter texts, analyze the whole text
                    result = self.sentiment_analyzer(text)[0]
                    score = 1 if result['label'] == 'POSITIVE' else 0
                    return self._map_sentiment_to_emotion(score)
            except Exception as e:
                logger.error(f"Error analyzing sentiment with model: {e}")
                # Fall through to fallback method
        
        # Fallback to TextBlob
        return self._textblob_sentiment(text)
    
    def _textblob_sentiment(self, text):
        """Fallback sentiment analysis using TextBlob"""
        try:
            analysis = TextBlob(text)
            # TextBlob polarity is between -1 (negative) and 1 (positive)
            # Normalize to 0-1 range
            normalized_score = (analysis.sentiment.polarity + 1) / 2
            return self._map_sentiment_to_emotion(normalized_score)
        except Exception as e:
            logger.error(f"Error in TextBlob sentiment analysis: {e}")
            return {"emotion": "neutral", "score": 0.5}
    
    def _map_sentiment_to_emotion(self, score):
        """Map numerical sentiment score to emotional category"""
        if score >= 0.8:
            emotion = "very positive"
        elif score >= 0.6:
            emotion = "positive"
        elif score >= 0.4:
            emotion = "neutral"
        elif score >= 0.2:
            emotion = "negative"
        else:
            emotion = "very negative"
        
        return {
            "emotion": emotion,
            "score": score
        }
    
    def cluster_entries(self, entries, n_clusters=5):
        """Cluster similar entries together"""
        if len(entries) < n_clusters:
            return [0] * len(entries)  # Not enough entries to cluster
        
        try:
            # Extract text content from entries
            texts = [entry.get('content', '') for entry in entries]
            
            # Create TF-IDF vectors
            vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
            X = vectorizer.fit_transform(texts)
            
            # Apply KMeans clustering
            kmeans = KMeans(n_clusters=min(n_clusters, len(entries)), random_state=42)
            clusters = kmeans.fit_predict(X)
            
            return clusters.tolist()
        except Exception as e:
            logger.error(f"Error clustering entries: {e}")
            return [0] * len(entries)  # Default cluster
    
    def extract_keywords(self, text, top_n=5):
        """Extract key phrases or topics from the text"""
        try:
            # Simple TF-IDF based keyword extraction
            vectorizer = TfidfVectorizer(max_features=100, stop_words='english')
            X = vectorizer.fit_transform([text])
            
            # Get feature names
            feature_names = vectorizer.get_feature_names_out()
            
            # Get TF-IDF scores
            scores = X.toarray()[0]
            
            # Sort by score
            sorted_indices = np.argsort(scores)[::-1]
            
            # Get top keywords
            keywords = [feature_names[i] for i in sorted_indices[:top_n]]
            return keywords
        except Exception as e:
            logger.error(f"Error extracting keywords: {e}")
            
            # Fallback: extract common words
            try:
                words = text.lower().split()
                # Remove common stop words
                stop_words = set(['the', 'and', 'a', 'to', 'of', 'in', 'i', 'is', 'that', 'it', 'was', 'for', 'on', 'with', 'as', 'be', 'this', 'my', 'me'])
                words = [word for word in words if word not in stop_words and len(word) > 3]
                
                # Count word frequencies
                from collections import Counter
                word_counts = Counter(words)
                
                # Get most common words
                return [word for word, _ in word_counts.most_common(top_n)]
            except Exception as e2:
                logger.error(f"Error in fallback keyword extraction: {e2}")
                return []

# Create a singleton instance
nlp_processor = NLPProcessor()

# Helper functions for easy access
def summarize_text(text, max_length=150, min_length=30):
    return nlp_processor.summarize_text(text, max_length, min_length)

def analyze_sentiment(text):
    return nlp_processor.analyze_sentiment(text)

def cluster_entries(entries, n_clusters=5):
    return nlp_processor.cluster_entries(entries, n_clusters)

def extract_keywords(text, top_n=5):
    return nlp_processor.extract_keywords(text, top_n)

# Example usage
if __name__ == "__main__":
    sample_text = """
    Today was an amazing day! I woke up feeling refreshed and energized. 
    The weather was perfect for a morning walk, so I spent about an hour 
    exploring the park near my house. I discovered a new trail that leads 
    to a beautiful pond. There were ducks and geese swimming peacefully. 
    It was so serene and calming. Later, I met with friends for lunch at 
    our favorite café. We had a great conversation about our future plans 
    and shared some laughs. I'm feeling grateful for these moments of joy 
    and connection. Looking forward to more days like this!
    """
    
    print("Original text:")
    print(sample_text)
    print("\nSummary:")
    print(summarize_text(sample_text))
    print("\nSentiment:")
    print(analyze_sentiment(sample_text))
    print("\nKeywords:")
    print(extract_keywords(sample_text))
