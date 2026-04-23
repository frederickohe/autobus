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
            # Log pre-search statistics
            logger.info(f"[RAG DEBUG] Starting vector search for user: {user_id}")
            logger.debug(f"[RAG DEBUG] Query embedding dimensions: {len(query_embedding)}")
            logger.debug(f"[RAG DEBUG] Search parameters - top_k: {top_k}, threshold: {threshold}")
            
            # Get statistics BEFORE search
            stats_query = text("""
                SELECT 
                    COUNT(*) as total_docs,
                    COUNT(*) FILTER (WHERE embedding IS NOT NULL) as docs_with_embeddings,
                    COUNT(*) FILTER (WHERE embedding IS NULL) as docs_without_embeddings
                FROM ai_training_files
                WHERE user_id = :user_id
            """)
            
            stats = self.db.execute(
                stats_query,
                {"user_id": user_id}
            ).fetchone()
            
            logger.info(
                f"[RAG DEBUG] Pre-search stats for user {user_id}: "
                f"total_docs={stats[0]}, docs_with_embeddings={stats[1]}, "
                f"docs_without_embeddings={stats[2]}"
            )
            
            # Convert embedding to pgvector format: '[0.1, 0.2, ..., 0.5]'
            embedding_str = str(query_embedding)
            
            # Log ALL documents for this user (for debugging)
            all_docs_query = text("""
                SELECT id, file_name, embedding IS NOT NULL as has_embedding, 
                       COALESCE(1 - (embedding <-> :query_embedding), 0) as similarity
                FROM ai_training_files
                WHERE user_id = :user_id
                ORDER BY similarity DESC
            """)
            
            all_docs = self.db.execute(
                all_docs_query,
                {
                    "query_embedding": embedding_str,
                    "user_id": user_id
                }
            ).fetchall()
            
            logger.debug(f"[RAG DEBUG] All documents for user {user_id}:")
            for doc in all_docs:
                logger.debug(
                    f"  - ID: {doc[0]}, Name: {doc[1]}, "
                    f"Has Embedding: {doc[2]}, Similarity: {doc[3]:.4f}"
                )
            
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
            
            logger.debug(
                f"[RAG DEBUG] Executing search with threshold={threshold}, top_k={top_k}"
            )
            
            results = self.db.execute(
                query,
                {
                    "query_embedding": embedding_str,
                    "user_id": user_id,
                    "threshold": threshold,
                    "top_k": top_k
                }
            ).fetchall()
            
            logger.info(
                f"[RAG DEBUG] Search returned {len(results)} results for user {user_id}"
            )
            
            # Format results and log each one
            formatted_results = [
                (row[3], row[4], row[1])  # (content, similarity, file_name)
                for row in results
            ]
            
            if formatted_results:
                for i, (content, similarity, file_name) in enumerate(formatted_results, 1):
                    logger.debug(
                        f"[RAG DEBUG] Result {i}: file={file_name}, "
                        f"similarity={similarity:.4f}, content_length={len(content)}"
                    )
            else:
                logger.warning(
                    f"[RAG DEBUG] No documents found matching threshold {threshold} "
                    f"for user {user_id}"
                )
            
            logger.info(
                f"[RAG DEBUG] Search complete: Found {len(formatted_results)} similar documents "
                f"for user {user_id} with threshold {threshold}"
            )
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"[RAG DEBUG] Vector search failed: {str(e)}", exc_info=True)
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
            logger.info(
                f"[RAG DEBUG] search_by_text called - query_text='{query_text}', "
                f"user_id={user_id}, top_k={top_k}"
            )
            
            results = self.search_similar_documents(
                query_embedding=query_embedding,
                user_id=user_id,
                top_k=top_k
            )
            
            logger.info(
                f"[RAG DEBUG] search_by_text results: {len(results)} documents returned"
            )
            
            # Convert to dict format
            dict_results = [
                {
                    "content": content,
                    "similarity": float(similarity),
                    "file_name": file_name
                }
                for content, similarity, file_name in results
            ]
            
            return dict_results
            
        except Exception as e:
            logger.error(
                f"[RAG DEBUG] Text-based search failed for query: {query_text}",
                exc_info=True
            )
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
            
            stats = {
                "total_documents": result[0],
                "documents_with_embeddings": result[1],
                "documents_without_embeddings": result[2]
            }
            
            logger.info(
                f"[RAG DEBUG] Embedding statistics for user {user_id}: "
                f"total={stats['total_documents']}, "
                f"with_embeddings={stats['documents_with_embeddings']}, "
                f"without_embeddings={stats['documents_without_embeddings']}"
            )
            
            return stats
            
        except Exception as e:
            logger.error(
                f"[RAG DEBUG] Failed to get embedding statistics: {str(e)}", 
                exc_info=True
            )
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
