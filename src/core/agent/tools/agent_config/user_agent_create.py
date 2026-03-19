from smolagents.tools import Tool
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
import json
from core.agent.tools.agent_config.user_agent_config_service import AgentConfigService


def _sanitize_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize parameters by stripping whitespace from string values.
    
    This fixes issues where LLMs might introduce unintended spaces or newlines
    in generated values (e.g., "noreply@useautobus. com" instead of "noreply@useautobus.com").
    
    Args:
        params: Dictionary of parameters to sanitize
        
    Returns:
        Dictionary with whitespace stripped from string values
    """
    sanitized = {}
    for key, value in params.items():
        if isinstance(value, str):
            sanitized[key] = value.strip()
        else:
            sanitized[key] = value
    return sanitized


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
            return json.dumps({"ok": False, "message": "Database session not initialized"})
        
        try:
            # Sanitize parameters to remove unintended whitespace
            params = _sanitize_params(params)
            
            metadata = {"status": status.strip() if isinstance(status, str) else status}
            if description:
                metadata["description"] = description.strip() if isinstance(description, str) else description
                
            result = self.service.create_or_update_agent(
                user_id=user_id,
                agent_name=agent_name,
                params=params,
                **metadata
            )
            
            if result.get("ok"):
                return json.dumps({"ok": True, "message": f"Agent {agent_name} configured successfully", "agent": result.get("agent")})
            else:
                return json.dumps({"ok": False, "message": result.get("message")})
        except Exception as e:
            return json.dumps({"ok": False, "message": f"Error creating agent: {str(e)}"})
