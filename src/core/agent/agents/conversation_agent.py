"""Conversation Sub-Agent

Handles multi-turn conversations and message routing."""

from smolagents import ToolCallingAgent
from sqlalchemy.orm import Session
from typing import Union
import logging

from core.agent.tools.conversation.conversation import ConversationTool

logger = logging.getLogger(__name__)


class ConversationAgent:
    """Sub-agent for managing conversations."""
    
    def __init__(self, model: Union[object, None], db_session: Session):
        """Initialize the Conversation Agent.
        
        Args:
            model: The model to use for this agent (e.g., InferenceClientModel or OpenAI wrapper).
            db_session: SQLAlchemy database session for database operations.
        """
        self.model = model
        self.db_session = db_session
        
        # Initialize conversation tool
        self.conversation_tool = ConversationTool()
        
        # Initialize the agent
        self.agent = ToolCallingAgent(
            tools=[self.conversation_tool],
            model=model,
            max_steps=5,
            name="conversation_agent",
            description="Manages conversational interactions. Handles multi-turn conversations and message routing.",
        )
    
    def process(self, message: str, user_id: str, conversation_history: list = None) -> str:
        """Process a conversational message.
        
        Args:
            message: The user's message.
            user_id: The user identifier.
            conversation_history: Optional conversation history.
            
        Returns:
            The agent's response.
        """
        try:
            context = f"User ID: {user_id}\n"
            if conversation_history:
                context += "Recent conversation:\n"
                for msg in conversation_history[-5:]:
                    context += f"{msg.get('role', 'user')}: {msg.get('content', '')}\n"
            context += f"\nCurrent message: {message}"
            
            logger.info(f"Conversation Agent processing for user {user_id}")
            response = self.agent.run(context)
            return response
        except Exception as e:
            logger.error(f"Error in Conversation Agent: {e}", exc_info=True)
            return f"Error processing conversation: {e}"
