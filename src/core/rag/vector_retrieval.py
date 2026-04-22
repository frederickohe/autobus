"""
Vector Retrieval Service - Semantic search using pgvector

Queries the PostgreSQL database with pgvector for similar documents.
Uses cosine similarity for text embeddings.
"""

import logging
from typing import List, Tuple, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session
from core.cloudstorage.model.aitrainingfilemodel import AITrainingFileModel

logger = logging.getLogger(__name__)


class VectorRetrieval:
    """Service for semantic search using pgvector."""
    
    # Similarity search defaults
    DEFAULT_TOP_K = 5  # Number of results to return
    SIMILARITY_THRESHOLD = 0.5  # Minimum cosine similarity (0 = orthogonal, 1 = identical)
    
    def __init__(self, db_session: Session):
        """
        Initialize vector retrieval service.
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
    
    def search_similar_documents(
        self,
        query_embedding: List[float],
        user_id: str,
        top_k: int = DEFAULT_TOP_K,
        threshold: float = SIMILARITY_THRESHOLD
    ) -> List[Tuple[str, float, str]]:
        """
        Search for documents similar to the query embedding.
        
        Uses cosine similarity (<-> operator) for fast approximate nearest neighbor search.
        Requires pgvector extension and IVFFLAT index on embedding column.
        
        Args:
            query_embedding: Query vector embedding (list of floats)
            user_id: Filter results by user_id
            top_k: Number of results to return
            threshold: Minimum cosine similarity score (0-1)
            
        Returns:
            List of tuples: (document_content, similarity_score, file_name)
            Sorted by similarity score (highest first)
            
        Raises:
            ValueError: If query_embedding is invalid
            Exception: If database query fails
        """
        if not query_embedding or len(query_embedding) == 0:
            raise ValueError("Query embedding cannot be empty")
        
        if not isinstance(query_embedding, list):
            raise ValueError("Query embedding must be a list")
        
        try:
            # Convert embedding to pgvector format: '[0.1, 0.2, ..., 0.5]'
            embedding_str = str(query_embedding)
            
            # Raw SQL query using pgvector's <-> operator (cosine distance)
            # Formula: similarity = 1 - cosine_distance
            query = text("""
                SELECT 
                    id,
                    file_name,
                    file_url,
                    content,
                    1 - (embedding <-> :query_embedding) as similarity
                FROM ai_training_files
                WHERE user_id = :user_id
                AND embedding IS NOT NULL
                AND 1 - (embedding <-> :query_embedding) >= :threshold
                ORDER BY embedding <-> :query_embedding
                LIMIT :top_k
            """)
            
            results = self.db.execute(
                query,
                {
                    "query_embedding": embedding_str,
                    "user_id": user_id,
                    "threshold": threshold,
                    "top_k": top_k
                }
            ).fetchall()
            
            # Format results
            formatted_results = [
                (row[3], row[4], row[1])  # (content, similarity, file_name)
                for row in results
            ]
            
            logger.info(
                f"Found {len(formatted_results)} similar documents for user {user_id} "
                f"with threshold {threshold}"
            )
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Vector search failed: {str(e)}")
            raise
    
    def search_by_text(
        self,
        query_text: str,
        query_embedding: List[float],
        user_id: str,
        top_k: int = DEFAULT_TOP_K
    ) -> List[dict]:
        """
        Search for documents similar to query text (high-level API).
        
        Args:
            query_text: Original query text (for logging)
            query_embedding: Pre-computed embedding of the query
            user_id: Filter by user_id
            top_k: Number of results
            
        Returns:
            List of dictionaries with keys: content, similarity, file_name, file_url
        """
        try:
            results = self.search_similar_documents(
                query_embedding=query_embedding,
                user_id=user_id,
                top_k=top_k
            )
            
            # Convert to dict format
            return [
                {
                    "content": content,
                    "similarity": float(similarity),
                    "file_name": file_name
                }
                for content, similarity, file_name in results
            ]
            
        except Exception as e:
            logger.error(f"Text-based search failed for query: {query_text}")
            logger.error(str(e))
            raise
    
    def get_embedding_statistics(self, user_id: str) -> dict:
        """
        Get statistics about embeddings for a user.
        
        Args:
            user_id: User ID to get stats for
            
        Returns:
            Dictionary with statistics
        """
        try:
            query = text("""
                SELECT 
                    COUNT(*) as total_documents,
                    COUNT(*) FILTER (WHERE embedding IS NOT NULL) as documents_with_embeddings,
                    COUNT(*) FILTER (WHERE embedding IS NULL) as documents_without_embeddings
                FROM ai_training_files
                WHERE user_id = :user_id
            """)
            
            result = self.db.execute(
                query,
                {"user_id": user_id}
            ).fetchone()
            
            return {
                "total_documents": result[0],
                "documents_with_embeddings": result[1],
                "documents_without_embeddings": result[2]
            }
            
        except Exception as e:
            logger.error(f"Failed to get embedding statistics: {str(e)}")
            raise
    
    def hybrid_search(
        self,
        query_embedding: List[float],
        query_text: str,
        user_id: str,
        top_k: int = DEFAULT_TOP_K,
        alpha: float = 0.7
    ) -> List[dict]:
        """
        Hybrid search combining vector similarity and keyword matching.
        
        Future enhancement: Combine pgvector results with BM25 keyword search.
        
        Args:
            query_embedding: Vector embedding of query
            query_text: Original query text
            user_id: User ID to filter by
            top_k: Number of results
            alpha: Weight for vector search (1-alpha for keyword search)
            
        Returns:
            List of search results
        """
        # For now, just do vector search
        # Can be enhanced to include BM25 keyword search
        return self.search_by_text(
            query_text=query_text,
            query_embedding=query_embedding,
            user_id=user_id,
            top_k=top_k
        )
