"""
RAG Pipeline Tool for LangChain Agents

Implements Retrieval-Augmented Generation (RAG) for intelligent chatbot responses.
Orchestrates the full pipeline:
  1. Generate query embedding
  2. Retrieve similar documents from pgvector
  3. Generate final answer using retrieved context

Architecture:
  User Question
    ↓
  OpenAI (embedding)
    ↓
  PostgreSQL + pgvector (semantic search)
    ↓
  OpenAI (generate answer)
    ↓
  Final Answer ✅
"""

import logging
import json
from typing import Optional, List, ClassVar, Any
from pydantic import BaseModel, Field, ConfigDict
from langchain.tools import BaseTool
from langchain_openai import ChatOpenAI
from sqlalchemy.orm import Session

from core.rag.embedding_service import EmbeddingService
from core.rag.vector_retrieval import VectorRetrieval

logger = logging.getLogger(__name__)


class RAGQueryInput(BaseModel):
    """Input schema for RAG pipeline tool."""
    
    query: str = Field(
        ...,
        description="The user's question to answer using RAG"
    )
    user_id: str = Field(
        ...,
        description="User ID to filter knowledge base documents"
    )
    top_k: int = Field(
        default=5,
        description="Number of similar documents to retrieve (1-10)"
    )
    include_sources: bool = Field(
        default=True,
        description="Include source file names in the response"
    )


class RAGPipelineTool(BaseTool):
    """
    LangChain tool for Retrieval-Augmented Generation pipeline.
    
    Combines semantic search with LLM to answer questions based on user's knowledge base.
    """
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    name: str = "rag_search"
    description: str = (
        "Search the user's knowledge base using semantic search and generate "
        "an answer powered by RAG (Retrieval-Augmented Generation). "
        "Returns a comprehensive answer based on retrieved documents."
    )
    args_schema: type = RAGQueryInput
    
    # Pydantic fields for database and service dependencies
    db: Optional[Session] = None
    embedding_service: Optional[Any] = None
    vector_retrieval: Optional[Any] = None
    llm: Optional[Any] = None
    
    # Configuration
    LLM_MODEL: ClassVar[str] = "gpt-4o-mini"
    EMBEDDING_MODEL: ClassVar[str] = "text-embedding-3-small"
    RESPONSE_TOKENS: ClassVar[int] = 500
    TEMPERATURE: ClassVar[float] = 0.3
    
    def __init__(self, db_session: Session, api_key: Optional[str] = None):
        """
        Initialize RAG pipeline tool.
        
        Args:
            db_session: SQLAlchemy database session
            api_key: OpenAI API key (optional, uses env var if not provided)
        """
        super().__init__()
        self.db = db_session
        self.embedding_service = EmbeddingService(api_key=api_key)
        self.vector_retrieval = VectorRetrieval(db_session)
        
        # Initialize LLM for answer generation
        self.llm = ChatOpenAI(
            model_name=self.LLM_MODEL,
            temperature=self.TEMPERATURE,
            max_tokens=self.RESPONSE_TOKENS,
            api_key=api_key
        )
        
        logger.info("RAG Pipeline Tool initialized successfully")
    
    def _run(self, query: str, user_id: str, top_k: int = 5, include_sources: bool = True) -> str:
        """
        Execute the RAG pipeline synchronously.
        
        Process:
        1. Generate embedding for the query
        2. Search for similar documents using pgvector
        3. Generate answer using retrieved context
        
        Args:
            query: User's question
            user_id: User ID for document filtering
            top_k: Number of documents to retrieve
            include_sources: Whether to include source citations
            
        Returns:
            Generated answer with optional source citations
        """
        try:
            logger.info(f"RAG Pipeline: Processing query from user {user_id}")
            
            # Validate inputs
            if not query or not query.strip():
                return "❌ Error: Query cannot be empty"
            
            if top_k < 1 or top_k > 10:
                top_k = 5  # Reset to default if invalid
            
            # Step 1: Generate query embedding
            logger.debug("Step 1: Generating query embedding...")
            try:
                query_embedding = self.embedding_service.generate_embedding(query)
                logger.debug(f"Generated embedding with {len(query_embedding)} dimensions")
            except Exception as e:
                logger.error(f"Embedding generation failed: {str(e)}")
                return f"❌ Error generating embedding: {str(e)}"
            
            # Step 2: Retrieve similar documents using pgvector
            logger.debug("Step 2: Retrieving similar documents...")
            try:
                similar_docs = self.vector_retrieval.search_by_text(
                    query_text=query,
                    query_embedding=query_embedding,
                    user_id=user_id,
                    top_k=top_k
                )
                
                if not similar_docs:
                    logger.warning(f"No similar documents found for user {user_id}")
                    return (
                        "❌ No relevant documents found in your knowledge base. "
                        "Please upload documents related to your query."
                    )
                
                logger.info(f"Retrieved {len(similar_docs)} similar documents")
                
            except Exception as e:
                logger.error(f"Document retrieval failed: {str(e)}")
                return f"❌ Error retrieving documents: {str(e)}"
            
            # Step 3: Build context from retrieved documents
            context_parts = []
            sources = []
            
            for i, doc in enumerate(similar_docs, 1):
                context_parts.append(f"[Document {i}]\n{doc['content']}")
                if include_sources and doc.get('file_name'):
                    sources.append(f"- {doc['file_name']} (similarity: {doc['similarity']:.2%})")
            
            context = "\n\n".join(context_parts)
            
            # Step 4: Generate answer using LLM with retrieved context
            logger.debug("Step 3: Generating answer using LLM...")
            try:
                system_prompt = (
                    "You are a helpful AI assistant. Answer the user's question based on "
                    "the provided documents. If the answer is not in the documents, say so clearly. "
                    "Be concise and accurate."
                )
                
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Context documents:\n{context}\n\nQuestion: {query}"}
                ]
                
                response = self.llm.invoke(messages)
                answer = response.content
                
                logger.info("Answer generated successfully")
                
                # Add source citations if requested
                if include_sources and sources:
                    answer += "\n\n📚 **Sources:**\n" + "\n".join(sources)
                
                return answer
                
            except Exception as e:
                logger.error(f"Answer generation failed: {str(e)}")
                return f"❌ Error generating answer: {str(e)}"
        
        except Exception as e:
            logger.error(f"RAG pipeline error: {str(e)}")
            return f"❌ RAG pipeline error: {str(e)}"
    
    async def _arun(self, query: str, user_id: str, top_k: int = 5, include_sources: bool = True) -> str:
        """
        Execute the RAG pipeline asynchronously.
        
        For now, wraps the synchronous implementation.
        Can be enhanced for true async operations.
        """
        # TODO: Implement true async operations for embedding and retrieval
        return self._run(query, user_id, top_k, include_sources)
    
    def get_knowledge_base_stats(self, user_id: str) -> dict:
        """
        Get statistics about a user's knowledge base.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with statistics
        """
        try:
            stats = self.vector_retrieval.get_embedding_statistics(user_id)
            logger.info(f"Knowledge base stats for user {user_id}: {stats}")
            return stats
        except Exception as e:
            logger.error(f"Failed to get knowledge base stats: {str(e)}")
            return {"error": str(e)}
