from smolagents.tools import Tool
from typing import Optional
from sqlalchemy.orm import Session
from core.agent.tools.agent_config.user_agent_config_service import AgentConfigService


class ListAgentsTool(Tool):
    """Tool for listing all agent configurations for a user."""
    
    name = "user_agent_config_list_agents_tool"
    description = (
        "List all agent configurations for a user. "
        "Returns a dictionary of all configured agents with their settings. "
        "Use this to see what agents are available for the user."
    )
    inputs = {
        "user_id": {
            "type": "string",
            "description": "The unique identifier of the user.",
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

    def forward(self, user_id: str) -> str:
        """List all agent configurations for a user.
        
        Args:
            user_id: The ID of the user
            
        Returns:
            JSON string with list of agents or error message
        """
        if not self.service:
            return '{"ok": false, "message": "Database session not initialized"}'
        
        try:
            result = self.service.list_agents(user_id=user_id)
            
            if result.get("ok"):
                return f'{{"ok": true, "agents": {result.get("agents")}}}'
            else:
                return f'{{"ok": false, "message": "{result.get("message")}"}}'
        except Exception as e:
            return f'{{"ok": false, "message": "Error listing agents: {str(e)}"}}'
