"""Video Generation Sub-Agent

Handles video generation and processing."""

from smolagents import ToolCallingAgent, InferenceClientModel, load_tool
from sqlalchemy.orm import Session
import logging

from core.agent.utils.image_storage import ImageStorageManager

logger = logging.getLogger(__name__)


class VideoGenerationAgent:
    """Sub-agent for video generation operations."""
    
    def __init__(self, model: InferenceClientModel, db_session: Session):
        """Initialize the Video Generation Agent.
        
        Args:
            model: The InferenceClientModel to use for this agent.
            db_session: SQLAlchemy database session for database operations.
        """
        self.model = model
        self.db_session = db_session
        
        # Initialize image storage manager (can be used for video files too)
        self.media_storage = ImageStorageManager()
        
        # Load video generation tools
        try:
            self.video_generation_tool = load_tool("agents-course/text-to-video", trust_remote_code=True)
            logger.info("Loaded text-to-video tool")
        except Exception as e:
            logger.warning(f"Could not load text-to-video tool: {e}. Video generation may be limited.")
            self.video_generation_tool = None
        
        # Initialize the agent with available tools
        tools = []
        if self.video_generation_tool:
            tools.append(self.video_generation_tool)
        
        self.agent = ToolCallingAgent(
            tools=tools if tools else [],
            model=model,
            max_steps=5,
            name="video_generation_agent",
            description="Generates videos from text descriptions. Can create and process videos.",
        )
    
    def process(self, message: str, user_id: str = None) -> str:
        """Process a video generation request.
        
        Args:
            message: The description or request for video generation.
            user_id: Optional user identifier for storing generated videos.
            
        Returns:
            The agent's response with video generation result or file path.
        """
        try:
            context = message
            if user_id:
                context = f"User ID: {user_id}\n{message}"
            
            logger.info(f"Video Generation Agent processing: {message[:100]}")
            
            if not self.video_generation_tool:
                return "Video generation tool is not available. Please ensure the required dependencies are installed."
            
            response = self.agent.run(context)
            return response
        except Exception as e:
            logger.error(f"Error in Video Generation Agent: {e}", exc_info=True)
            return f"Error generating video: {e}"
