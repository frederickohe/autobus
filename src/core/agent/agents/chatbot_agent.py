"""Chatbot Sub-Agent

Handles RAG-based question answering and document retrieval."""

from smolagents import ToolCallingAgent, InferenceClientModel
from sqlalchemy.orm import Session
import logging

from core.agent.tools.rag.retriever import RetrieverTool
from core.agent.tools.rag.document_management import (
    UploadDocumentTool,
    GetDocumentsTool,
    DeleteDocumentTool,
)

logger = logging.getLogger(__name__)


class ChatbotAgent:
    """Sub-agent for RAG-based chatbot operations."""
    
    def __init__(self, model: InferenceClientModel, db_session: Session):
        """Initialize the Chatbot Agent.
        
        Args:
            model: The InferenceClientModel to use for this agent.
            db_session: SQLAlchemy database session for database operations.
        """
        self.model = model
        self.db_session = db_session
        
        # Initialize RAG tools
        self.retriever_tool = RetrieverTool()
        self.upload_document_tool = UploadDocumentTool(db_session)
        self.get_documents_tool = GetDocumentsTool(db_session)
        self.delete_document_tool = DeleteDocumentTool(db_session)
        
        # Initialize the agent
        self.agent = ToolCallingAgent(
            tools=[
                self.retriever_tool,
                self.upload_document_tool,
                self.get_documents_tool,
                self.delete_document_tool,
            ],
            model=model,
            max_steps=6,
            name="chatbot_agent",
            description="RAG-based chatbot agent. Uses retriever tool to answer questions based on uploaded documents. Can manage document uploads, retrieval, and deletion.",
        )
    
    def process(self, message: str, user_id: str = None) -> str:
        """Process a chatbot/RAG query.
        
        Args:
            message: The user's question or request.
            user_id: Optional user identifier for personalized document retrieval.
            
        Returns:
            The agent's response based on retrieved documents or operation result.
        """
        try:
            # Set user documents for retriever if user_id provided
            if user_id:
                self.retriever_tool.set_user_docs(user_id)
                context = f"User ID: {user_id}\n{message}"
            else:
                context = message
            
            logger.info(f"Chatbot Agent processing: {message[:100]}")
            response = self.agent.run(context)
            return response
        except Exception as e:
            logger.error(f"Error in Chatbot Agent: {e}", exc_info=True)
            return f"Error processing chatbot query: {e}"
