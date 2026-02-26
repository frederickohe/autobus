from smolagents import CodeAgent, DuckDuckGoSearchTool, InferenceClientModel, load_tool, tool
import datetime
import pytz
import yaml
from typing import Optional
from sqlalchemy.orm import Session

from core.agent.tools.answer.final_answer import FinalAnswerTool
from core.agent.tools.conversation.conversation import ConversationTool
from core.agent.tools.email.email import EmailTool
from core.agent.tools.agent_config import (
    CreateAgentTool,
    GetAgentTool,
    UpdateAgentTool,
    DeleteAgentTool,
    ListAgentsTool,
)

class AutoBus:
    def __init__(self, prompts_path: str = "src/core/agent/prompts.yaml", db_session: Optional[Session] = None):
        """Initialize the Autobus agent.
        
        Args:
            prompts_path: Path to the prompts YAML configuration file.
            db_session: Optional SQLAlchemy database session for agent config operations.
        """
        self.model = InferenceClientModel(
            max_tokens=2096,
            temperature=0.5,
            model_id='Qwen/Qwen2.5-Coder-32B-Instruct',
        )
        
        with open(prompts_path, 'r') as stream:
            prompt_templates = yaml.safe_load(stream)
        
        self.final_answer = FinalAnswerTool()
        self.assistant_conversation = ConversationTool()
        self.email = EmailTool()
        self.image_generation = load_tool("agents-course/text-to-image", trust_remote_code=True)
        
        # Initialize agent config tools with database session
        self.user_agent_config_create_tool = CreateAgentTool(db_session)
        self.user_agent_config_get_tool = GetAgentTool(db_session)
        self.user_agent_config_update_tool = UpdateAgentTool(db_session)
        self.user_agent_config_delete_tool = DeleteAgentTool(db_session)
        self.user_agent_config_list_agents_tool = ListAgentsTool(db_session)
        
        self.agent = CodeAgent(
            model=self.model,
            tools=[
                self.final_answer,
                self.assistant_conversation,
                self.email,
                self.image_generation,
                DuckDuckGoSearchTool(),
                self.user_agent_config_create_tool,
                self.user_agent_config_get_tool,
                self.user_agent_config_update_tool,
                self.user_agent_config_delete_tool,
                self.user_agent_config_list_agents_tool,
            ],
            max_steps=6,
            verbosity_level=1,
            planning_interval=None,
            name=None,
            description=None,
            prompt_templates=prompt_templates
        )
        
    def process_user_message(self, userid: str, message: str, agent_name: str) -> str:
        """Process a user message through the Autobus agent.
        
        Args:
            userid: Identifier for the user sending the message.
            message: The user's message text.
            has_active_subscription: Whether the user has an active subscription.
            
        Returns:
            The agent's response.
        """
        try:
            response = self.agent.run(f"User ID: {userid}, agent_name: {agent_name}, Message: {message}")
            return response
        except Exception as e:
            return f"Error processing message with Autobus: {e}"