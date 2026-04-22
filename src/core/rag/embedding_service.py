"""
Embedding Service - Generates and manages vector embeddings for RAG pipeline

Uses OpenAI's text-embedding-3-small model for efficient, high-quality embeddings.
Handles caching and batch processing for performance.
"""

import os
import json
import logging
from typing import List, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating vector embeddings using OpenAI."""
    
    # OpenAI embedding model configuration
    MODEL_NAME = "text-embedding-3-small"
    EMBEDDING_DIM = 1536  # Dimension of text-embedding-3-small
    MAX_TOKENS_PER_INPUT = 8191  # Max tokens for embedding model
    BATCH_SIZE = 100  # Process embeddings in batches
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the embedding service.
        
        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
        """
        if api_key is None:
            api_key = os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        self.client = OpenAI(api_key=api_key)
        logger.info(f"EmbeddingService initialized with model: {self.MODEL_NAME}")
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate a single embedding for the given text.
        
        Args:
            text: Text to embed
            
        Returns:
            List of floats representing the embedding vector
            
        Raises:
            ValueError: If text is empty
            Exception: If OpenAI API call fails
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        
        # Truncate if needed
        text = text[:self.MAX_TOKENS_PER_INPUT * 4]  # Rough truncation
        
        try:
            response = self.client.embeddings.create(
                input=text,
                model=self.MODEL_NAME
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {str(e)}")
            raise
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts efficiently.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
            
        Raises:
            ValueError: If texts list is empty
            Exception: If OpenAI API call fails
        """
        if not texts:
            raise ValueError("Texts list cannot be empty")
        
        embeddings = []
        
        # Process in batches for efficiency
        for i in range(0, len(texts), self.BATCH_SIZE):
            batch = texts[i : i + self.BATCH_SIZE]
            
            # Truncate texts if needed
            batch = [text[:self.MAX_TOKENS_PER_INPUT * 4] for text in batch]
            
            try:
                response = self.client.embeddings.create(
                    input=batch,
                    model=self.MODEL_NAME
                )
                
                # Extract embeddings in order
                batch_embeddings = [item.embedding for item in response.data]
                embeddings.extend(batch_embeddings)
                
                logger.debug(f"Generated embeddings for batch {i//self.BATCH_SIZE + 1}")
                
            except Exception as e:
                logger.error(f"Failed to generate batch embeddings: {str(e)}")
                raise
        
        return embeddings
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of the embeddings."""
        return self.EMBEDDING_DIM
    
    def validate_embedding(self, embedding: List[float]) -> bool:
        """
        Validate that an embedding has the correct dimensions.
        
        Args:
            embedding: Embedding vector to validate
            
        Returns:
            True if valid, False otherwise
        """
        return (
            isinstance(embedding, list) and
            len(embedding) == self.EMBEDDING_DIM and
            all(isinstance(x, (int, float)) for x in embedding)
        )
