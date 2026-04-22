"""
Document Processing Service for RAG

Handles document upload, chunking, embedding generation, and storage.
Processes documents asynchronously for the knowledge base.
"""

import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from core.rag.embedding_service import EmbeddingService
from core.cloudstorage.model.aitrainingfilemodel import AITrainingFileModel

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Process documents for RAG: chunk, embed, and store."""
    
    # Document processing configuration
    CHUNK_SIZE = 500  # Characters per chunk
    CHUNK_OVERLAP = 50  # Overlap between chunks for context
    
    def __init__(self, db_session: Session, api_key: Optional[str] = None):
        """
        Initialize document processor.
        
        Args:
            db_session: SQLAlchemy database session
            api_key: OpenAI API key (optional)
        """
        self.db = db_session
        self.embedding_service = EmbeddingService(api_key=api_key)
    
    def chunk_document(self, text: str) -> List[str]:
        """
        Split document into overlapping chunks.
        
        Args:
            text: Document content to chunk
            
        Returns:
            List of text chunks
        """
        if not text or not text.strip():
            return []
        
        chunks = []
        start = 0
        
        while start < len(text):
            # Get chunk
            end = min(start + self.CHUNK_SIZE, len(text))
            chunk = text[start:end].strip()
            
            if chunk:
                chunks.append(chunk)
            
            # Move start position with overlap
            start = end - self.CHUNK_OVERLAP
            
            if start <= 0:
                break
        
        logger.debug(f"Split document into {len(chunks)} chunks")
        return chunks
    
    def embed_and_store_document(
        self,
        file_id: int,
        document_content: str,
        user_id: str
    ) -> bool:
        """
        Process a document: chunk, embed, and store embeddings.
        
        For now, stores embedding of the entire document.
        Future: Can store per-chunk embeddings.
        
        Args:
            file_id: ID of the file record in database
            document_content: Full document content
            user_id: User ID for this document
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not document_content or not document_content.strip():
                logger.warning(f"Document {file_id} is empty")
                return False
            
            logger.info(f"Processing document {file_id} for user {user_id}")
            
            # Generate embedding for entire document
            # For better results, could use document summary
            embedding = self.embedding_service.generate_embedding(document_content)
            
            # Update database record with embedding
            file_record = self.db.query(AITrainingFileModel).filter(
                AITrainingFileModel.id == file_id
            ).first()
            
            if not file_record:
                logger.error(f"File record {file_id} not found")
                return False
            
            file_record.embedding = embedding
            self.db.commit()
            
            logger.info(f"Successfully embedded document {file_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to embed document {file_id}: {str(e)}")
            self.db.rollback()
            return False
    
    def embed_and_store_batch(
        self,
        documents: List[tuple],  # List of (file_id, content, user_id)
        batch_size: int = 10
    ) -> int:
        """
        Process multiple documents in batches.
        
        Args:
            documents: List of (file_id, content, user_id) tuples
            batch_size: Number of documents to process per batch
            
        Returns:
            Number of successfully processed documents
        """
        if not documents:
            logger.warning("No documents to process")
            return 0
        
        success_count = 0
        
        for i, (file_id, content, user_id) in enumerate(documents):
            if self.embed_and_store_document(file_id, content, user_id):
                success_count += 1
            
            if (i + 1) % batch_size == 0:
                logger.info(f"Processed {i + 1}/{len(documents)} documents")
        
        logger.info(f"Batch processing complete: {success_count}/{len(documents)} successful")
        return success_count
    
    def reprocess_document_embeddings(
        self,
        user_id: str,
        file_ids: Optional[List[int]] = None
    ) -> int:
        """
        Reprocess embeddings for user's documents.
        
        Useful after updating embedding model or fixing errors.
        
        Args:
            user_id: User ID
            file_ids: Specific file IDs to reprocess (None = all for user)
            
        Returns:
            Number of reprocessed documents
        """
        try:
            # Query documents to reprocess
            query = self.db.query(AITrainingFileModel).filter(
                AITrainingFileModel.user_id == user_id
            )
            
            if file_ids:
                query = query.filter(AITrainingFileModel.id.in_(file_ids))
            
            documents = query.all()
            
            if not documents:
                logger.warning(f"No documents found for user {user_id}")
                return 0
            
            logger.info(f"Reprocessing {len(documents)} documents for user {user_id}")
            
            success_count = 0
            for doc in documents:
                # TODO: Retrieve actual document content from cloud storage
                # For now, this is a placeholder
                logger.debug(f"Reprocessing document {doc.id}: {doc.file_name}")
                # Generate new embedding
                # embed_result = self.embed_and_store_document(doc.id, content, user_id)
                # if embed_result:
                #     success_count += 1
            
            return success_count
            
        except Exception as e:
            logger.error(f"Failed to reprocess embeddings for user {user_id}: {str(e)}")
            return 0
