from smolagents import ToolCallingAgent
from smolagents.agent_types import AgentImage, AgentAudio
import yaml
import logging
import re
from typing import Optional
from sqlalchemy.orm import Session

from core.agent.tools.answer.final_answer import FinalAnswerTool
from core.conversationmanager.service.conversation_manager import ConversationManager
from core.agent.utils.image_storage import ImageStorageManager
from core.llmclient.openai_model_wrapper import OpenAIModelForSmolagents
import OpenAIModelForSmolagents as OpenAI

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
        """Initialize the Autobus manager agent with sub-agents.
        
        Args:
            prompts_path: Path to the prompts YAML configuration file.
            db_session: Optional SQLAlchemy database session for agent config operations.
        """
        # Initialize OpenAI model for smolagents
        self.model = OpenAI(
            model="gpt-4",
            temperature=0.5,
            max_tokens=2096
        )
        
        with open(prompts_path, 'r') as stream:
            prompt_templates = yaml.safe_load(stream)
        
        # Ensure authorized_imports is available in templates if not already defined
        if 'authorized_imports' not in prompt_templates:
            prompt_templates['authorized_imports'] = "math, datetime, json, re, csv, os, sys, collections, itertools, functools, operator, statistics, requests, pandas, numpy, pathlib, typing, urllib"
        
        # Initialize conversation manager for tracking user conversations
        self.conversation_manager = ConversationManager()
        
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
        
        # Initialize the manager agent with direct access to FinalAnswerTool and managed sub-agents
        self.agent = initialize_agent(
            tools=[self.final_answer],
            llm=self.model,
            agent="zero-shot-react-description",
            verbose=True
        )
    
    def process_user_message(self, userid: str, message: str, agent_name: str) -> str:
        """Process a user message through the Autobus multi-agent system.
        
        The manager agent automatically routes the request to appropriate sub-agents:
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
            The agent's response (can be string, AgentImage, or AgentAudio).
        """
        try:
            # Get conversation state for user
            state = self.conversation_manager.get_conversation_state(userid)
            
            # Normalize file paths in the message to prevent LLM from misinterpreting them
            normalized_message = normalize_file_paths(message)
            
            # Add user message to history
            logger.info("Received message from %s: %s", userid, (normalized_message or '')[:200])
            self.conversation_manager.update_conversation_history(userid, "user", normalized_message)
            
            # Format conversation context with recent history
            conversation_context = self._format_conversation_context(state.conversation_history)
            
            # Build complete prompt with conversation history and user context
            # For RAG: set user documents in chatbot agent
            if self.chatbot_agent.retriever_tool:
                self.chatbot_agent.retriever_tool.set_user_docs(userid)
            
            complete_message = f"User ID: {userid}, agent_name: {agent_name}\n\nConversation History:\n{conversation_context}\n\nCurrent Message: {normalized_message}"
            
            # Process message through manager agent
            response = self.agent.run(complete_message)
            
            # Handle media responses (images/audio) by saving them and storing reference in conversation history
            if isinstance(response, (AgentImage, AgentAudio)):
                file_path, conversation_string = self.image_storage.handle_media_response(response, userid)
                # Store only the reference string in conversation history, not the actual media object
                self.conversation_manager.update_conversation_history(userid, "assistant", conversation_string)
                logger.info(f"Saved media file for user {userid}: {file_path}")
                # Return the original media object so the API caller still gets it
                return f"Image generated and saved: {file_path}"
            else:
                # For text responses, store directly
                self.conversation_manager.update_conversation_history(userid, "assistant", str(response))
                return response
            
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
