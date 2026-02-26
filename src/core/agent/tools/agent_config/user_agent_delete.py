from smolagents.tools import Tool
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from core.agent.tools.agent_config.user_agent_config_service import AgentConfigService


class DeleteAgentTool(Tool):
    """Tool for deleting an agent configuration."""
    
    name = "user_agent_config_delete_tool"
    description = (
        "Delete an agent configuration for a user. "
        "Removes the agent and all its settings from the user's account. "
        "Use this to remove agents that are no longer needed."
    )
    inputs = {
        "user_id": {
            "type": "string",
            "description": "The unique identifier of the user.",
            "required": True
        },
        "agent_name": {
            "type": "string",
            "description": "The name of the agent to delete.",
            "required": True
        }
    }
    output_type = "string"

    def __init__(self, db_session: Optional[Session] = None):
        """Initialize the tool with a database session.
        
        Args:
            db_session: SQLAlchemy database session for performing queries.
        """
        super().__init__()
        self.db_session = db_session
        self.service = AgentConfigService(db_session) if db_session else None

    def forward(self, user_id: str, agent_name: str) -> str:
        """Delete an agent configuration.
        
        Args:
            user_id: The ID of the user
            agent_name: Name of the agent to delete
            
        Returns:
            JSON string with success/error information
        """
        if not self.service:
            return '{"ok": false, "message": "Database session not initialized"}'
        
        try:
            result = self.service.delete_agent(user_id=user_id, agent_name=agent_name)
            
            if result.get("ok"):
                return f'{{"ok": true, "message": "Agent {agent_name} deleted successfully"}}'
            else:
                return f'{{"ok": false, "message": "{result.get("message")}"}}'
        except Exception as e:
            return f'{{"ok": false, "message": "Error deleting agent: {str(e)}"}}'