"""RAG (Retrieval-Augmented Generation) Module

Implements semantic search and answer generation using pgvector and OpenAI.

Key Components:
- EmbeddingService: Generates vector embeddings using OpenAI
- VectorRetrieval: Semantic search using pgvector
- DocumentProcessor: Document chunking and embedding management
- RAGPipelineTool: LangChain tool for complete RAG pipeline
- UpdatedRetrieverTool: LangChain-compatible semantic search tool
- UpdatedUploadDocumentTool: Document upload with automatic embedding
- GetDocumentsTool: List user's documents
"""

from .embedding_service import EmbeddingService
from .vector_retrieval import VectorRetrieval
from .document_processor import DocumentProcessor
from .rag_pipeline_tool import RAGPipelineTool, RAGQueryInput
from .updated_retriever_tool import UpdatedRetrieverTool, RetrieverInput
from .updated_document_management import (
    UpdatedUploadDocumentTool,
    GetDocumentsTool,
    UploadDocumentInput,
    GetDocumentsInput,
)

__all__ = [
    "EmbeddingService",
    "VectorRetrieval",
    "DocumentProcessor",
    "RAGPipelineTool",
    "RAGQueryInput",
    "UpdatedRetrieverTool",
    "RetrieverInput",
    "UpdatedUploadDocumentTool",
    "GetDocumentsTool",
    "UploadDocumentInput",
    "GetDocumentsInput",
]
