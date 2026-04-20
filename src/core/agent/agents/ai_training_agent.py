"""AI Training Sub-Agent

Handles model training, fine-tuning, and AI-related operations."""

from smolagents import ToolCallingAgent, InferenceClientModel
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)


class AITrainingAgent:
    """Sub-agent for AI training and model operations."""
    
    def __init__(self, model: InferenceClientModel, db_session: Session):
        """Initialize the AI Training Agent.
        
        Args:
            model: The InferenceClientModel to use for this agent.
            db_session: SQLAlchemy database session for database operations.
        """
        self.model = model
        self.db_session = db_session
        
        # Initialize AI training tools (can be extended with actual training tools)
        self.tools = []
        
        # Initialize the agent
        self.agent = ToolCallingAgent(
            tools=self.tools,
            model=model,
            max_steps=10,
            name="ai_training_agent",
            description="Handles AI model training, fine-tuning, and AI-related operations. Can manage training jobs and model optimization.",
        )
    
    def process(self, message: str, user_id: str = None) -> str:
        """Process an AI training request.
        
        Args:
            message: The user's training request or query.
            user_id: Optional user identifier.
            
        Returns:
            The agent's response with training results or status.
        """
        try:
            context = message
            if user_id:
                context = f"User ID: {user_id}\n{message}"
            
            logger.info(f"AI Training Agent processing: {message[:100]}")
            
            # For now, return a placeholder response
            # This can be extended when actual training tools are available
            response = self.agent.run(context)
            return response
        except Exception as e:
            logger.error(f"Error in AI Training Agent: {e}", exc_info=True)
            return f"Error processing AI training request: {e}"
