"""
Updated Retriever Tool - LangChain Compatible with pgvector Support

Replaces BM25-based retrieval with semantic search using pgvector.
Maintains backward compatibility while providing superior results.
"""

import logging
from typing import Optional
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
from sqlalchemy.orm import Session

from core.rag.embedding_service import EmbeddingService
from core.rag.vector_retrieval import VectorRetrieval

logger = logging.getLogger(__name__)


class RetrieverInput(BaseModel):
    """Input schema for retriever tool."""
    
    query: str = Field(
        ...,
        description="The query to search for in documents. Be specific and use key terms."
    )
    user_id: str = Field(
        ...,
        description="The user ID whose documents to retrieve from"
    )
    top_k: int = Field(
        default=5,
        description="Number of document chunks to retrieve (1-20)"
    )
    similarity_threshold: float = Field(
        default=0.5,
        description="Minimum similarity score (0-1) for results"
    )


class UpdatedRetrieverTool(BaseTool):
    """
    Updated retriever tool for semantic search using pgvector.
    
    Replaces old BM25 retrieval with vector-based semantic search.
    Requires pgvector extension and embeddings in ai_training_files table.
    """
    
    name: str = "retriever"
    description: str = (
        "Search through your uploaded documents to find relevant information using "
        "semantic search. Returns the most relevant document passages for your query."
    )
    args_schema: type = RetrieverInput
    
    def __init__(self, db_session: Session, api_key: Optional[str] = None):
        """
        Initialize updated retriever tool.
        
        Args:
            db_session: SQLAlchemy database session
            api_key: OpenAI API key (optional)
        """
        super().__init__()
        self.db = db_session
        self.embedding_service = EmbeddingService(api_key=api_key)
        self.vector_retrieval = VectorRetrieval(db_session)
    
    def _run(
        self,
        query: str,
        user_id: str,
        top_k: int = 5,
        similarity_threshold: float = 0.5
    ) -> str:
        """
        Retrieve documents using semantic search.
        
        Args:
            query: Search query
            user_id: User ID for document filtering
            top_k: Number of results to return
            similarity_threshold: Minimum similarity score
            
        Returns:
            Formatted string with retrieved documents
        """
        try:
            if not query or not query.strip():
                return "Error: Query cannot be empty"
            
            # Validate parameters
            if top_k < 1 or top_k > 20:
                top_k = 5
            
            if similarity_threshold < 0 or similarity_threshold > 1:
                similarity_threshold = 0.5
            
            logger.info(
                f"[RAG DEBUG] Retriever._run called - query='{query}', "
                f"user_id={user_id}, top_k={top_k}, threshold={similarity_threshold}"
            )
            
            # Check document stats BEFORE generating embedding
            try:
                pre_stats = self.vector_retrieval.get_embedding_statistics(user_id)
                logger.info(
                    f"[RAG DEBUG] Pre-retrieval stats: user {user_id} has "
                    f"{pre_stats['documents_with_embeddings']} documents with embeddings "
                    f"({pre_stats['total_documents']} total)"
                )
            except Exception as e:
                logger.warning(f"[RAG DEBUG] Could not get pre-retrieval stats: {str(e)}")
            
            # Generate query embedding
            try:
                logger.debug(f"[RAG DEBUG] Generating embedding for query: '{query}'")
                query_embedding = self.embedding_service.generate_embedding(query)
                logger.debug(
                    f"[RAG DEBUG] Query embedding generated successfully "
                    f"(dimensions: {len(query_embedding)})"
                )
            except Exception as e:
                logger.error(
                    f"[RAG DEBUG] Failed to generate query embedding: {str(e)}",
                    exc_info=True
                )
                return f"Error generating embedding: {str(e)}"
            
            # Search for similar documents
            try:
                logger.info(
                    f"[RAG DEBUG] Starting vector search with threshold={similarity_threshold}"
                )
                results = self.vector_retrieval.search_by_text(
                    query_text=query,
                    query_embedding=query_embedding,
                    user_id=user_id,
                    top_k=top_k
                )
                logger.info(f"[RAG DEBUG] Vector search returned {len(results)} results")
            except Exception as e:
                logger.error(
                    f"[RAG DEBUG] Vector search failed: {str(e)}", 
                    exc_info=True
                )
                return f"Error searching documents: {str(e)}"
            
            if not results:
                logger.warning(
                    f"[RAG DEBUG] No relevant documents found for user {user_id} "
                    f"with query '{query}' and threshold {similarity_threshold}"
                )
                return (
                    "No relevant documents found. Please upload documents related to your query."
                )
            
            # Format results
            output_parts = []
            for i, doc in enumerate(results, 1):
                output_parts.append(
                    f"[Document {i}] (Relevance: {doc['similarity']:.1%})\n"
                    f"Source: {doc['file_name']}\n"
                    f"Content: {doc['content'][:500]}...\n"
                )
                logger.debug(
                    f"[RAG DEBUG] Result {i}: {doc['file_name']}, "
                    f"similarity={doc['similarity']:.4f}"
                )
            
            output = "\n".join(output_parts)
            logger.info(
                f"[RAG DEBUG] Retrieval complete: Retrieved {len(results)} documents "
                f"for user {user_id}"
            )
            
            return output
            
        except Exception as e:
            logger.error(
                f"[RAG DEBUG] Retriever error: {str(e)}", 
                exc_info=True
            )
            return f"Error retrieving documents: {str(e)}"
    
    async def _arun(
        self,
        query: str,
        user_id: str,
        top_k: int = 5,
        similarity_threshold: float = 0.5
    ) -> str:
        """Async version of _run."""
        return self._run(query, user_id, top_k, similarity_threshold)
    
    def get_user_document_count(self, user_id: str) -> int:
        """Get number of documents (with embeddings) for a user."""
        try:
            stats = self.vector_retrieval.get_embedding_statistics(user_id)
            return stats.get("documents_with_embeddings", 0)
        except Exception as e:
            logger.error(f"Failed to get document count: {str(e)}")
            return 0
