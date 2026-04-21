"""Email Sub-Agent

Handles email composition and sending operations."""

from smolagents import ToolCallingAgent
from sqlalchemy.orm import Session
from typing import Union
import logging

from core.agent.tools.email.email import EmailTool

logger = logging.getLogger(__name__)


class EmailAgent:
    """Sub-agent for email operations."""
    
    def __init__(self, model: Union[object, None], db_session: Session):
        """Initialize the Email Agent.
        
        Args:
            model: The model to use for this agent (e.g., InferenceClientModel or OpenAI wrapper).
            db_session: SQLAlchemy database session for database operations.
        """
        self.model = model
        self.db_session = db_session
        
        # Initialize email tool
        self.email_tool = EmailTool()
        
        # Initialize the agent
        self.agent = ToolCallingAgent(
            tools=[self.email_tool],
            model=model,
            max_steps=5,
            name="email_agent",
            description="Handles email composition and sending. Can compose and send emails for various purposes.",
        )
    
    def process(self, message: str, user_id: str = None) -> str:
        """Process an email request.
        
        Args:
            message: The user's email request (e.g., 'Send an email to john@example.com about the project').
            user_id: Optional user identifier.
            
        Returns:
            The agent's response with email operation result.
        """
        try:
            context = message
            if user_id:
                context = f"User ID: {user_id}\n{message}"
            
            logger.info(f"Email Agent processing: {message[:100]}")
            response = self.agent.run(context)
            return response
        except Exception as e:
            logger.error(f"Error in Email Agent: {e}", exc_info=True)
            return f"Error processing email request: {e}"
