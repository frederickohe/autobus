"""Email Sub-Agent

Handles email composition and sending operations using LangChain."""

from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from sqlalchemy.orm import Session
from typing import Any
import logging

from core.agent.tools.email.email import EmailTool

logger = logging.getLogger(__name__)


class EmailAgent:
    """Sub-agent for email operations using LangChain."""
    
    def __init__(self, model: Any, db_session: Session):
        """Initialize the Email Agent with LangChain.
        
        Args:
            model: The LangChain LLM model to use for this agent (e.g., ChatOpenAI).
            db_session: SQLAlchemy database session for database operations.
        """
        self.model = model
        self.db_session = db_session
        
        # Initialize email tool
        self.email_tool = EmailTool()
        
        # Create list of tools
        self.tools = [self.email_tool]
        
        # Create system prompt for the agent
        system_prompt = """You are a helpful email composition and sending agent.
        
You can help users compose and send emails for various purposes.

When helping users:
1. Gather necessary email information (recipient, subject, body)
2. Use the email tool to send emails with the provided configuration
3. Confirm the email has been sent successfully

Always be clear about what email is being sent and to whom."""
        
        # Create ReAct agent with the tools
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
        
        logger.info("EmailAgent initialized with LangChain")
    
    def process(self, message: str, user_id: str = None) -> str:
        """Process an email request.
        
        Args:
            message: The user's email request (e.g., 'Send an email to john@example.com about the project').
            user_id: Optional user identifier.
            
        Returns:
            The agent's response with email operation result.
        """
        try:
            context = message
            if user_id:
                context = f"User ID: {user_id}\n{message}"
            
            logger.info(f"Email Agent processing: {message[:100]}")
            response = self.executor.invoke({"input": context})
            
            # Extract output from the response
            if isinstance(response, dict):
                return response.get("output", str(response))
            return str(response)
        except Exception as e:
            logger.error(f"Error in Email Agent: {e}", exc_info=True)
            return f"Error processing email request: {e}"
