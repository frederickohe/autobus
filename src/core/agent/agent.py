from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
import yaml
import logging
import re
from typing import Optional, Any
from sqlalchemy.orm import Session

from core.agent.tools.answer.final_answer import FinalAnswerTool
from core.agent.utils.image_storage import ImageStorageManager

# Import sub-agents
from core.agent.agents import (
    ConfigAgent,
    EmailAgent,
    ImageGenerationAgent,
    VideoGenerationAgent,
    ChatbotAgent,
    WebSearchAgent,
    ProductsAgent,
)

logger = logging.getLogger(__name__)

def normalize_file_paths(text: str) -> str:
    """Normalize file paths in text by removing extra spaces.
    
    Fixes issues where LLM might add spaces in file paths like:
    'C:\path\Autobus_Conceptnote. docx' -> 'C:\path\Autobus_Conceptnote.docx'
    
    Args:
        text: Text that may contain file paths.
        
    Returns:
        Text with normalized file paths.
    """
    # Pattern to match Windows paths with spaces before extensions or between path components
    # Handles cases like "filename. ext" -> "filename.ext"
    text = re.sub(r'(\w)\s+(\.\w+)', r'\1\2', text)
    
    # Handle spaces in path separators (rare but possible)
    # E.g., "folder \ folder" -> "folder\folder"
    text = re.sub(r'\s+\\\s+', r'\\', text)
    text = re.sub(r'\s+/\s+', r'/', text)
    
    return text

class AutoBus:
    def __init__(self, prompts_path: str = "src/core/agent/prompts.yaml", db_session: Optional[Session] = None):
        """Initialize the Autobus manager agent with sub-agents using LangChain.
        
        Args:
            prompts_path: Path to the prompts YAML configuration file.
            db_session: Optional SQLAlchemy database session for agent config operations.
        """
        # Initialize LangChain ChatOpenAI model
        self.model = ChatOpenAI(
            model_name="gpt-4",
            temperature=0.5,
            max_tokens=2096
        )
        
        with open(prompts_path, 'r') as stream:
            prompt_templates = yaml.safe_load(stream)
        
        # Ensure authorized_imports is available in templates if not already defined
        if 'authorized_imports' not in prompt_templates:
            prompt_templates['authorized_imports'] = "math, datetime, json, re, csv, os, sys, collections, itertools, functools, operator, statistics, requests, pandas, numpy, pathlib, typing, urllib"
        
        # Initialize image storage manager for handling agent-generated media
        self.image_storage = ImageStorageManager()
        
        self.db_session = db_session
        
        # Initialize the FinalAnswerTool directly for the manager agent
        self.final_answer = FinalAnswerTool()
        
        # Initialize all sub-agents
        self.config_agent = ConfigAgent(self.model, db_session)
        self.email_agent = EmailAgent(self.model, db_session)
        self.image_generation_agent = ImageGenerationAgent(self.model, db_session)
        self.video_generation_agent = VideoGenerationAgent(self.model, db_session)
        self.chatbot_agent = ChatbotAgent(self.model, db_session)
        self.web_search_agent = WebSearchAgent(self.model, db_session)
        self.products_agent = ProductsAgent(self.model, db_session)
        
        # Create system prompt for manager agent
        manager_system_prompt = """You are AutoBus, a sophisticated multi-agent orchestrator.

You coordinate multiple specialized sub-agents to help users with various tasks:
- config_agent: Manages agent configurations
- email_agent: Handles email operations
- image_generation_agent: Generates images
- video_generation_agent: Creates videos
- chatbot_agent: Answers questions using RAG
- web_search_agent: Searches the web
- products_agent: Manages products

Route requests to the appropriate sub-agent and synthesize their responses.
When a user asks for something, determine which agent(s) to use and coordinate them.
Always provide clear, helpful responses."""
        
        # Create tools list for the manager agent
        tools = [self.final_answer]
        
        # Create the manager agent using ReAct pattern
        self.agent = create_react_agent(
            llm=self.model,
            tools=tools,
            prompt=PromptTemplate.from_template(
                manager_system_prompt + 
                "\n\nAvailable Tools:\n{tools}\n\nTool Names: {tool_names}\n\nUser: {input}\n\nThink about which sub-agents to use.\nAgent Scratchpad:\n{agent_scratchpad}"
            )
        )
        
        # Wrap in AgentExecutor
        self.executor = AgentExecutor.from_agent_and_tools(
            agent=self.agent,
            tools=tools,
            verbose=True,
            max_iterations=10,
            handle_parsing_errors=True,
        )
        
        logger.info("AutoBus initialized with LangChain")
    
    def process_user_message(self, userid: str, message: str, agent_name: str) -> str:
        """Process a user message through the Autobus multi-agent system.
        
        The manager agent routes the request to appropriate sub-agents:
        - config_agent: Agent configuration management
        - email_agent: Email operations
        - image_generation_agent: Image generation requests
        - video_generation_agent: Video generation requests
        - chatbot_agent: RAG-based question answering
        - web_search_agent: Web search and page retrieval
        
        Args:
            userid: Identifier for the user sending the message.
            message: The user's message text.
            agent_name: Name of the agent/sub-agent if specifically targeted.
            
        Returns:
            The agent's response.
        """
        try:
            
            # Add user message to history
            logger.info("Received message from %s: %s", userid, (message or '')[:200])

            # Build complete prompt with conversation history and user context
            # For RAG: set user documents in chatbot agent
            if hasattr(self.chatbot_agent, 'retriever_tool') and self.chatbot_agent.retriever_tool:
                self.chatbot_agent.retriever_tool.set_user_docs(userid)
            
            complete_message = f"User ID: {userid}, agent_name: {agent_name}\n\nCurrent Message: {message}"
            
            # Process message through manager agent
            response = self.executor.invoke({"input": complete_message})
            
            # Extract output from response
            if isinstance(response, dict):
                result = response.get("output", str(response))
            else:
                result = str(response)
    
            return result
            
        except Exception as e:
            logger.error(f"Error processing message with Autobus for user {userid}: {e}", exc_info=True)
            return f"Error processing message with Autobus: {e}"
    
    def _format_conversation_context(self, conversation_history: list) -> str:
        """Format conversation history for inclusion in the prompt.
        
        Args:
            conversation_history: List of conversation messages with role and content.
            
        Returns:
            Formatted conversation context string.
        """
        if not conversation_history:
            return "[No previous conversation]"
        
        # Format recent messages (exclude the message just added, as it's mentioned separately)
        formatted_messages = []
        for msg in conversation_history[-20:]:  # Keep last 20 messages for context
            role = msg.get("role", "unknown").capitalize()
            content = msg.get("content", "")
            timestamp = msg.get("timestamp", "")
            formatted_messages.append(f"{role}: {content}")
        
        return "\n".join(formatted_messages) if formatted_messages else "[No previous conversation]"
