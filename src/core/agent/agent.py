from smolagents import CodeAgent, DuckDuckGoSearchTool, InferenceClientModel, load_tool, tool
from smolagents.agent_types import AgentImage, AgentAudio
import datetime
import pytz
import yaml
import logging
from typing import Optional
from sqlalchemy.orm import Session

from core.agent.tools.answer.final_answer import FinalAnswerTool
from core.agent.tools.conversation.conversation import ConversationTool
from core.agent.tools.email.email import EmailTool
from core.agent.tools.generate_image.generate_image import ImageGenerationTool
from core.agent.tools.agent_config import (
    CreateAgentTool,
    GetAgentTool,
    UpdateAgentTool,
    DeleteAgentTool,
    ListAgentsTool,
)
from core.agent.tools.product import (
    CreateProductTool,
    GetProductTool,
    UpdateProductTool,
    FetchProductByNameTool,
    UserSelectProductTool,
    GetProductInventoryTool,
    IncrementInventoryTool,
    DecrementInventoryTool,
)
from core.agent.tools.rag.retriever import RetrieverTool
from core.agent.tools.rag.document_management import (
    UploadDocumentTool,
    GetDocumentsTool,
    DeleteDocumentTool,
)
from core.conversationmanager.service.conversation_manager import ConversationManager
from core.agent.utils.image_storage import ImageStorageManager

logger = logging.getLogger(__name__)

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
        
        # Initialize conversation manager for tracking user conversations
        self.conversation_manager = ConversationManager()
        
        # Initialize image storage manager for handling agent-generated images
        self.image_storage = ImageStorageManager()
        
        self.db_session = db_session
        
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
        
        # Initialize product tools with database session
        self.product_create_tool = CreateProductTool(db_session)
        self.product_get_tool = GetProductTool(db_session)
        self.product_update_tool = UpdateProductTool(db_session)
        self.product_fetch_by_name_tool = FetchProductByNameTool(db_session)
        self.product_user_select_tool = UserSelectProductTool(db_session)
        self.product_inventory_get_tool = GetProductInventoryTool(db_session)
        self.inventory_increment_tool = IncrementInventoryTool(db_session)
        self.inventory_decrement_tool = DecrementInventoryTool(db_session)
        
        #Initialize RAG tools (retriever, document management)
        self.retriever_tool = RetrieverTool()
        self.upload_document_tool = UploadDocumentTool(db_session)
        self.get_documents_tool = GetDocumentsTool(db_session)
        self.delete_document_tool = DeleteDocumentTool(db_session)
        
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
                self.product_create_tool,
                self.product_get_tool,
                self.product_update_tool,
                self.product_fetch_by_name_tool,
                self.product_user_select_tool,
                self.product_inventory_get_tool,
                self.inventory_increment_tool,
                self.inventory_decrement_tool,
                self.retriever_tool,
                self.upload_document_tool,
                self.get_documents_tool,
                self.delete_document_tool,
            ],
            max_steps=6,
            verbosity_level=1,
            planning_interval=None,
            name=None,
            description=None,
            prompt_templates=prompt_templates
        )
        
    def process_user_message(self, userid: str, message: str, agent_name: str) -> str:
        """Process a user message through the Autobus agent with conversation history and RAG.
        
        Args:
            userid: Identifier for the user sending the message.
            message: The user's message text.
            agent_name: Name of the agent to process the message.
            
        Returns:
            The agent's response (can be string, AgentImage, or AgentAudio).
        """
        try:
            # Set user documents for retriever
            self.retriever_tool.set_user_docs(userid)
            
            # Get conversation state for user
            state = self.conversation_manager.get_conversation_state(userid)
            
            # Add user message to history
            logger.info("Received message from %s: %s", userid, (message or '')[:200])
            self.conversation_manager.update_conversation_history(userid, "user", message)
            
            # Format conversation context with recent history
            conversation_context = self._format_conversation_context(state.conversation_history)
            
            # Build complete prompt with conversation history and user context
            complete_message = f"User ID: {userid}, agent_name: {agent_name}\n\nConversation History:\n{conversation_context}\n\nCurrent Message: {message}"
            
            # Process message through agent
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
