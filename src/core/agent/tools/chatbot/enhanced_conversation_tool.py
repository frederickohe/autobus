"""
Enhanced Chatbot Tool with RAG Support

Supports both conversational AI and knowledge-base aware responses.
Can switch between general conversation and RAG-powered answers.
"""

import logging
import os
from typing import Optional, Literal, ClassVar, Any, Dict
from pydantic import BaseModel, Field, ConfigDict
from langchain.tools import BaseTool
from langchain_openai import ChatOpenAI
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class EnhancedConversationInput(BaseModel):
    """Input schema for enhanced conversation tool."""
    
    message: str = Field(
        ...,
        description="The user's message to respond to"
    )
    user_id: str = Field(
        ...,
        description="User ID for RAG knowledge base filtering"
    )
    conversation_mode: Literal["general", "rag_aware"] = Field(
        default="general",
        description="'general' for regular conversation, 'rag_aware' for RAG-powered answers"
    )
    use_rag: bool = Field(
        default=False,
        description="Whether to use RAG pipeline for this query"
    )


class EnhancedConversationTool(BaseTool):
    """
    Enhanced conversation tool with optional RAG support.
    
    Can operate in two modes:
    1. General: Regular conversational AI without knowledge base context
    2. RAG-Aware: Uses user's knowledge base to provide informed answers
    """
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    name: str = "assistant_conversation"
    description: str = (
        "Generates a conversational response to a user message. "
        "Can optionally use RAG (Retrieval-Augmented Generation) to ground responses "
        "in the user's knowledge base. "
        "Use 'general' mode for small talk, 'rag_aware' mode for knowledge-based questions."
    )
    args_schema: type = EnhancedConversationInput
    
    # Pydantic fields for database and service dependencies
    db: Optional[Session] = None
    rag_tool: Optional[Any] = None
    client: Optional[Any] = None
    conversation_histories: Dict[str, list] = {}
    
    # Configuration
    LLM_MODEL: ClassVar[str] = "gpt-4o-mini"
    MAX_TOKENS: ClassVar[int] = 256
    TEMPERATURE: ClassVar[float] = 0.7
    MAX_CONVERSATION_HISTORY: ClassVar[int] = 20
    
    def __init__(
        self,
        db_session: Optional[Session] = None,
        rag_tool: Optional['RAGPipelineTool'] = None,  # RAG tool injection
        api_key: Optional[str] = None
    ):
        """
        Initialize enhanced conversation tool.
        
        Args:
            db_session: SQLAlchemy database session (for RAG)
            rag_tool: RAG pipeline tool (optional, for knowledge-base queries)
            api_key: OpenAI API key (optional, uses env var if not provided)
        """
        super().__init__()
        self.db = db_session
        self.rag_tool = rag_tool
        
        # Initialize LLM
        if api_key is None:
            api_key = os.environ.get("OPENAI_API_KEY")
        
        self.client = ChatOpenAI(
            model_name=self.LLM_MODEL,
            temperature=self.TEMPERATURE,
            max_tokens=self.MAX_TOKENS,
            api_key=api_key
        )
        
        # Conversation history per user (in-memory)
        self.conversation_histories = {}
        
        logger.info("Enhanced conversation tool initialized")
    
    def _run(
        self,
        message: str,
        user_id: str,
        conversation_mode: str = "general",
        use_rag: bool = False
    ) -> str:
        """
        Generate a response to the user message.
        
        Args:
            message: User's message
            user_id: User ID for conversation context
            conversation_mode: 'general' or 'rag_aware'
            use_rag: Whether to use RAG for this query
            
        Returns:
            Generated response
        """
        try:
            if not message or not message.strip():
                return "I didn't receive a message. Could you please try again?"
            
            # Prevent processing the same message twice
            if self._is_duplicate_message(user_id, message):
                logger.debug(f"Detected duplicate message for user {user_id}")
                return message
            
            # Add message to history
            self._add_to_history(user_id, {"role": "user", "content": message})
            
            # Route based on mode and RAG availability
            if use_rag and self.rag_tool and conversation_mode == "rag_aware":
                return self._handle_rag_aware_query(message, user_id)
            else:
                return self._handle_general_conversation(message, user_id)
            
        except Exception as e:
            logger.error(f"Error in conversation: {str(e)}")
            return f"❌ I encountered an error: {str(e)}. Please try again."
    
    async def _arun(
        self,
        message: str,
        user_id: str,
        conversation_mode: str = "general",
        use_rag: bool = False
    ) -> str:
        """Async version of _run."""
        return self._run(message, user_id, conversation_mode, use_rag)
    
    def _handle_general_conversation(self, message: str, user_id: str) -> str:
        """
        Handle general conversation without RAG.
        
        Args:
            message: User message
            user_id: User ID
            
        Returns:
            Generated response
        """
        try:
            history = self.conversation_histories.get(user_id, [])
            messages = [
                {
                    "role": "system",
                    "content": "You are a helpful and friendly AI assistant."
                }
            ] + history
            
            response = self.client.invoke(messages)
            assistant_message = response.content
            
            # Add response to history
            self._add_to_history(user_id, {"role": "assistant", "content": assistant_message})
            
            return assistant_message
            
        except Exception as e:
            logger.error(f"General conversation error: {str(e)}")
            raise
    
    def _handle_rag_aware_query(self, message: str, user_id: str) -> str:
        """
        Handle query with RAG support.
        
        Uses retrieved documents to ground the response.
        
        Args:
            message: User query
            user_id: User ID
            
        Returns:
            RAG-powered response
        """
        try:
            logger.info(f"Processing RAG-aware query from user {user_id}")
            
            # Use RAG tool to get answer
            response = self.rag_tool._run(
                query=message,
                user_id=user_id,
                top_k=5,
                include_sources=True
            )
            
            # Add response to history
            self._add_to_history(user_id, {"role": "assistant", "content": response})
            
            return response
            
        except Exception as e:
            logger.error(f"RAG-aware conversation error: {str(e)}")
            # Fallback to general conversation
            logger.info("Falling back to general conversation")
            return self._handle_general_conversation(message, user_id)
    
    def _is_duplicate_message(self, user_id: str, message: str) -> bool:
        """Check if message is a duplicate of last assistant response."""
        history = self.conversation_histories.get(user_id, [])
        if history:
            last = history[-1]
            if (last.get("role") == "assistant" and
                message.strip() == last.get("content", "").strip()):
                return True
        return False
    
    def _add_to_history(self, user_id: str, message: dict):
        """Add message to conversation history."""
        if user_id not in self.conversation_histories:
            self.conversation_histories[user_id] = []
        
        history = self.conversation_histories[user_id]
        history.append(message)
        
        # Truncate history if too long
        if len(history) > self.MAX_CONVERSATION_HISTORY * 2:
            self.conversation_histories[user_id] = history[-(self.MAX_CONVERSATION_HISTORY * 2):]
    
    def reset_conversation(self, user_id: str):
        """Clear conversation history for a user."""
        if user_id in self.conversation_histories:
            del self.conversation_histories[user_id]
            logger.info(f"Reset conversation history for user {user_id}")
    
    def get_conversation_history(self, user_id: str) -> list:
        """Get current conversation history for a user."""
        return self.conversation_histories.get(user_id, [])
