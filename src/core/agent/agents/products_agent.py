"""Products Sub-Agent

Handles product management, inventory, and user selection."""

from smolagents import ToolCallingAgent, InferenceClientModel
from sqlalchemy.orm import Session
import logging

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

logger = logging.getLogger(__name__)


class ProductsAgent:
    """Sub-agent for product management."""
    
    def __init__(self, model: InferenceClientModel, db_session: Session):
        """Initialize the Products Agent.
        
        Args:
            model: The InferenceClientModel to use for this agent.
            db_session: SQLAlchemy database session for database operations.
        """
        self.model = model
        self.db_session = db_session
        
        # Initialize product tools
        self.create_tool = CreateProductTool(db_session)
        self.get_tool = GetProductTool(db_session)
        self.update_tool = UpdateProductTool(db_session)
        self.fetch_by_name_tool = FetchProductByNameTool(db_session)
        self.user_select_tool = UserSelectProductTool(db_session)
        self.inventory_get_tool = GetProductInventoryTool(db_session)
        self.inventory_increment_tool = IncrementInventoryTool(db_session)
        self.inventory_decrement_tool = DecrementInventoryTool(db_session)
        
        # Initialize the agent
        self.agent = ToolCallingAgent(
            tools=[
                self.create_tool,
                self.get_tool,
                self.update_tool,
                self.fetch_by_name_tool,
                self.user_select_tool,
                self.inventory_get_tool,
                self.inventory_increment_tool,
                self.inventory_decrement_tool,
            ],
            model=model,
            max_steps=6,
            name="products_agent",
            description="Manages products, inventory, and user product selection. Can create, retrieve, update products and manage inventory levels.",
        )
    
    def process(self, message: str, user_id: str = None) -> str:
        """Process a product management request.
        
        Args:
            message: The user's product request.
            user_id: Optional user identifier for personalized product selection.
            
        Returns:
            The agent's response with product information or operation result.
        """
        try:
            context = message
            if user_id:
                context = f"User ID: {user_id}\n{message}"
            
            logger.info(f"Products Agent processing: {message[:100]}")
            response = self.agent.run(context)
            return response
        except Exception as e:
            logger.error(f"Error in Products Agent: {e}", exc_info=True)
            return f"Error processing product request: {e}"
