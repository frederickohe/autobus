"""Agent Configuration Sub-Agent for LangChain

Handles agent creation, retrieval, update, and deletion operations using LangChain framework."""

from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import Tool
from sqlalchemy.orm import Session
from typing import Union, List, Any
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
    """Sub-agent for managing agent configurations using LangChain."""
    
    def __init__(self, model: Any, db_session: Session):
        """Initialize the Config Agent with LangChain.
        
        Args:
            model: The LangChain LLM model to use for this agent (e.g., ChatOpenAI).
            db_session: SQLAlchemy database session for database operations.
        """
        self.model = model
        self.db_session = db_session
        
        # Initialize config tools as LangChain tools
        self.create_tool = CreateAgentTool(db_session)
        self.get_tool = GetAgentTool(db_session)
        self.update_tool = UpdateAgentTool(db_session)
        self.delete_tool = DeleteAgentTool(db_session)
        self.list_tool = ListAgentsTool(db_session)
        
        # Create list of tools for the agent
        self.tools = [
            self.create_tool,
            self.get_tool,
            self.update_tool,
            self.delete_tool,
            self.list_tool,
        ]
        
        # Create system prompt for the agent
        system_prompt = """You are a helpful agent that manages agent configurations.
        
You can create, retrieve, update, delete, and list agent configurations for users.

When helping users:
1. For creating agents: Use the create tool and ensure all required parameters are provided
2. For retrieving: Use the get tool to fetch specific agent configurations
3. For updating: Use the update tool to modify existing agent settings
4. For deleting: Use the delete tool to remove unwanted agent configurations
5. For listing: Use the list tool to show all configured agents for a user

Always be clear about what operations you're performing and their results."""
        
        # Create ReAct agent with the tools
        from langchain.prompts import PromptTemplate
        
        # Create the agent using create_react_agent
        self.agent = create_react_agent(
            llm=self.model,
            tools=self.tools,
            prompt=PromptTemplate.from_template(
                system_prompt + 
                "\n\nAvailable Tools:\n{tools}\n\nTool Names: {tool_names}\n\nUser: {input}\n\nThought process (agent scratchpad):\n{agent_scratchpad}"
            )
        )
        
        # Wrap in AgentExecutor
        self.executor = AgentExecutor.from_agent_and_tools(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            max_iterations=5,
            handle_parsing_errors=True,
        )
        
        logger.info("ConfigAgent initialized with LangChain")
    
    def process(self, message: str) -> str:
        """Process a message related to agent configuration.
        
        Args:
            message: The user's configuration management request.
            
        Returns:
            The agent's response.
        """
        try:
            logger.info(f"Config Agent processing: {message[:100]}")
            response = self.executor.invoke({"input": message})
            
            # Extract output from the response
            if isinstance(response, dict):
                return response.get("output", str(response))
            return str(response)
        except Exception as e:
            logger.error(f"Error in Config Agent: {e}", exc_info=True)
            return f"Error processing agent configuration request: {e}"
