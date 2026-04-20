"""Image Generation Sub-Agent

Handles image generation and processing."""

from smolagents import ToolCallingAgent, InferenceClientModel, load_tool
from sqlalchemy.orm import Session
import logging

from core.agent.utils.image_storage import ImageStorageManager

logger = logging.getLogger(__name__)


class ImageGenerationAgent:
    """Sub-agent for image generation operations."""
    
    def __init__(self, model: InferenceClientModel, db_session: Session):
        """Initialize the Image Generation Agent.
        
        Args:
            model: The InferenceClientModel to use for this agent.
            db_session: SQLAlchemy database session for database operations.
        """
        self.model = model
        self.db_session = db_session
        
        # Initialize image storage manager
        self.image_storage = ImageStorageManager()
        
        # Load the text-to-image tool
        try:
            self.image_generation_tool = load_tool("agents-course/text-to-image", trust_remote_code=True)
        except Exception as e:
            logger.warning(f"Could not load text-to-image tool: {e}")
            self.image_generation_tool = None
        
        # Initialize the agent
        tools = [self.image_generation_tool] if self.image_generation_tool else []
        
        self.agent = ToolCallingAgent(
            tools=tools if tools else [load_tool("agents-course/text-to-image", trust_remote_code=True)],
            model=model,
            max_steps=5,
            name="image_generation_agent",
            description="Generates images from text descriptions. Can create and process images.",
        )
    
    def process(self, message: str, user_id: str = None) -> str:
        """Process an image generation request.
        
        Args:
            message: The description or request for image generation.
            user_id: Optional user identifier for storing generated images.
            
        Returns:
            The agent's response with image generation result or file path.
        """
        try:
            context = message
            if user_id:
                context = f"User ID: {user_id}\n{message}"
            
            logger.info(f"Image Generation Agent processing: {message[:100]}")
            response = self.agent.run(context)
            return response
        except Exception as e:
            logger.error(f"Error in Image Generation Agent: {e}", exc_info=True)
            return f"Error generating image: {e}"
