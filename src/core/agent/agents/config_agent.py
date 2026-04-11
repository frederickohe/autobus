"""Agent Configuration Sub-Agent

Handles agent creation, retrieval, update, and deletion operations."""

from smolagents import CodeAgent, InferenceClientModel
from sqlalchemy.orm import Session
import logging

from core.agent.tools.agent_config import (
    CreateAgentTool,
    GetAgentTool,
    UpdateAgentTool,
    DeleteAgentTool,
    ListAgentsTool,
)

logger = logging.getLogger(__name__)


class ConfigAgent:
    """Sub-agent for managing agent configurations."""
    
    def __init__(self, model: InferenceClientModel, db_session: Session):
        """Initialize the Config Agent.
        
        Args:
            model: The InferenceClientModel to use for this agent.
            db_session: SQLAlchemy database session for database operations.
        """
        self.model = model
        self.db_session = db_session
        
        # Initialize config tools
        self.create_tool = CreateAgentTool(db_session)
        self.get_tool = GetAgentTool(db_session)
        self.update_tool = UpdateAgentTool(db_session)
        self.delete_tool = DeleteAgentTool(db_session)
        self.list_tool = ListAgentsTool(db_session)
        
        # Initialize the agent
        self.agent = CodeAgent(
            tools=[
                self.create_tool,
                self.get_tool,
                self.update_tool,
                self.delete_tool,
                self.list_tool,
            ],
            model=model,
            max_steps=5,
            name="config_agent",
            description="Manages agent configurations. Can create, retrieve, update, delete, and list agent configurations.",
        )
    
    def process(self, message: str) -> str:
        """Process a message related to agent configuration.
        
        Args:
            message: The user's configuration management request.
            
        Returns:
            The agent's response.
        """
        try:
            logger.info(f"Config Agent processing: {message[:100]}")
            response = self.agent.run(message)
            return response
        except Exception as e:
            logger.error(f"Error in Config Agent: {e}", exc_info=True)
            return f"Error processing agent configuration request: {e}"
