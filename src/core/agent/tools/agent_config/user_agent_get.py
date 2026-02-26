from smolagents.tools import Tool
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from core.agent.tools.agent_config.user_agent_config_service import AgentConfigService


class GetAgentTool(Tool):
    """Tool for retrieving an agent configuration."""
    
    name = "user_agent_config_get_tool"
    description = (
        "Retrieve a specific agent configuration for a user. "
        "Returns the agent's parameters and metadata. "
        "Use this to check if an agent is configured or to review agent settings."
    )
    inputs = {
        "user_id": {
            "type": "string",
            "description": "The unique identifier of the user.",
            "required": True
        },
        "agent_name": {
            "type": "string",
            "description": "The name of the agent to retrieve.",
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
        """Get a specific agent configuration.
        
        Args:
            user_id: The ID of the user
            agent_name: Name of the agent to retrieve
            
        Returns:
            JSON string with agent configuration or error message
        """
        if not self.service:
            return '{"ok": false, "message": "Database session not initialized"}'
        
        try:
            result = self.service.get_agent(user_id=user_id, agent_name=agent_name)
            
            if result.get("ok"):
                return f'{{"ok": true, "agent": {result.get("agent")}}}'
            else:
                return f'{{"ok": false, "message": "{result.get("message")}"}}'
        except Exception as e:
            return f'{{"ok": false, "message": "Error retrieving agent: {str(e)}"}}'