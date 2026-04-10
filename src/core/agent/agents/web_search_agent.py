"""Web Search Sub-Agent

Handles web searching and page content retrieval."""

from smolagents import ToolCallingAgent, InferenceClientModel, WebSearchTool, tool
from sqlalchemy.orm import Session
import logging
import re
import requests
from markdownify import markdownify
from requests.exceptions import RequestException


logger = logging.getLogger(__name__)


@tool
def visit_webpage(url: str) -> str:
    """Visits a webpage at the given URL and returns its content as a markdown string.
    
    Args:
        url: The URL of the webpage to visit.
    
    Returns:
        The content of the webpage converted to Markdown, or an error message if the request fails.
    """
    try:
        # Send a GET request to the URL
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # Convert the HTML content to Markdown
        markdown_content = markdownify(response.text).strip()
        
        # Remove multiple line breaks
        markdown_content = re.sub(r"\n{3,}", "\n\n", markdown_content)
        
        return markdown_content
    except RequestException as e:
        return f"Error fetching the webpage: {str(e)}"
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"


class WebSearchAgent:
    """Sub-agent for web search operations."""
    
    def __init__(self, model: InferenceClientModel, db_session: Session):
        """Initialize the Web Search Agent.
        
        Args:
            model: The InferenceClientModel to use for this agent.
            db_session: SQLAlchemy database session for database operations.
        """
        self.model = model
        self.db_session = db_session
        
        # Initialize web search tools
        self.web_search_tool = WebSearchTool()
        
        # Initialize the agent
        self.agent = ToolCallingAgent(
            tools=[
                self.web_search_tool,
                visit_webpage,
            ],
            model=model,
            max_steps=10,
            name="web_search_agent",
            description="Performs web searches and retrieves webpage content. Can search the web and extract information from web pages.",
        )
    
    def process(self, message: str, user_id: str = None) -> str:
        """Process a web search request.
        
        Args:
            message: The search query or request.
            user_id: Optional user identifier.
            
        Returns:
            The agent's response with search results and information.
        """
        try:
            context = message
            if user_id:
                context = f"User ID: {user_id}\n{message}"
            
            logger.info(f"Web Search Agent processing: {message[:100]}")
            response = self.agent.run(context)
            return response
        except Exception as e:
            logger.error(f"Error in Web Search Agent: {e}", exc_info=True)
            return f"Error performing web search: {e}"
