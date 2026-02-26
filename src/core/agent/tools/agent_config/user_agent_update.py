from smolagents.tools import Tool
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from core.agent.tools.agent_config.user_agent_config_service import AgentConfigService


class UpdateAgentTool(Tool):
    """Tool for updating an agent configuration."""
    
    name = "user_agent_config_update_tool"
    description = (
        "Update parameters for an existing agent configuration. "
        "Modifies agent settings, parameters, or status. "
        "Use this to adjust agent behavior or add/update configuration values."
    )
    inputs = {
        "user_id": {
            "type": "string",
            "description": "The unique identifier of the user.",
            "required": True
        },
        "agent_name": {
            "type": "string",
            "description": "The name of the agent to update.",
            "required": True
        },
        "params": {
            "type": "object",
            "description": "Dictionary of parameters to update (will be merged with existing params).",
            "required": True
        },
        "status": {
            "type": "string",
            "description": "Update the agent status ('active' or 'inactive'). Optional.",
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
        status: Optional[str] = None
    ) -> str:
        """Update agent configuration.
        
        Args:
            user_id: The ID of the user
            agent_name: Name of the agent to update
            params: Dictionary of parameters to update
            status: Optional new status for the agent
            
        Returns:
            JSON string with success/error information
        """
        if not self.service:
            return '{"ok": false, "message": "Database session not initialized"}'
        
        try:
            metadata = {}
            if status:
                metadata["status"] = status
                
            result = self.service.create_or_update_agent(
                user_id=user_id,
                agent_name=agent_name,
                params=params,
                **metadata
            )
            
            if result.get("ok"):
                return f'{{"ok": true, "message": "Agent {agent_name} updated successfully", "agent": {result.get("agent")}}}'
            else:
                return f'{{"ok": false, "message": "{result.get("message")}"}}'
        except Exception as e:
            return f'{{"ok": false, "message": "Error updating agent: {str(e)}"}}'