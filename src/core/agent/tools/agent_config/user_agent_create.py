from smolagents.tools import Tool
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from core.agent.tools.agent_config.user_agent_config_service import AgentConfigService


class CreateAgentTool(Tool):
    """Tool for creating or updating an agent configuration."""
    
    name = "user_agent_config_create_tool"
    description = (
        "Create or update an agent configuration for the user. "
        "Stores agent parameters and metadata needed for the agent to function properly. "
        "Use this to configure a new agent or update existing agent settings."
    )
    inputs = {
        "user_id": {
            "type": "string",
            "description": "The unique identifier of the user.",
            "required": True
        },
        "agent_name": {
            "type": "string",
            "description": "The name of the agent to create or update.",
            "required": True
        },
        "params": {
            "type": "object",
            "description": "Dictionary of parameters required by the agent (e.g., API keys, configuration settings).",
            "required": True
        },
        "status": {
            "type": "string",
            "description": "Status of the agent ('active' or 'inactive'). Defaults to 'active'.",
            "required": False,
            "nullable": True
        },
        "description": {
            "type": "string",
            "description": "Human-readable description of what this agent configuration does.",
            "required": False,
            "nullable": True
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

    def forward(
        self,
        user_id: str,
        agent_name: str,
        params: Dict[str, Any],
        status: str = "active",
        description: Optional[str] = None
    ) -> str:
        """Create or update an agent configuration.
        
        Args:
            user_id: The ID of the user
            agent_name: Name of the agent
            params: Dictionary of agent parameters
            status: Agent status (active/inactive)
            description: Optional description of the agent
            
        Returns:
            JSON string with success/error information
        """
        if not self.service:
            return '{"ok": false, "message": "Database session not initialized"}'
        
        try:
            metadata = {"status": status}
            if description:
                metadata["description"] = description
                
            result = self.service.create_or_update_agent(
                user_id=user_id,
                agent_name=agent_name,
                params=params,
                **metadata
            )
            
            if result.get("ok"):
                return f'{{"ok": true, "message": "Agent {agent_name} configured successfully", "agent": {result.get("agent")}}}'
            else:
                return f'{{"ok": false, "message": "{result.get("message")}"}}'
        except Exception as e:
            return f'{{"ok": false, "message": "Error creating agent: {str(e)}"}}'
