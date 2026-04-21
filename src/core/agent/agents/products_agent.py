"""Products Sub-Agent

Handles product management operations including CRUD operations and inventory management."""

from smolagents import ToolCallingAgent
from sqlalchemy.orm import Session
from typing import Union
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
    """Sub-agent for product management operations."""
    
    def __init__(self, model: Union[object, None], db_session: Session):
        """Initialize the Products Agent.
        
        Args:
            model: The model to use for this agent (e.g., InferenceClientModel or OpenAI wrapper).
            db_session: SQLAlchemy database session for database operations.
        """
        self.model = model
        self.db_session = db_session
        
        # Initialize product tools
        self.create_product_tool = CreateProductTool(db_session)
        self.get_product_tool = GetProductTool(db_session)
        self.update_product_tool = UpdateProductTool(db_session)
        self.fetch_product_by_name_tool = FetchProductByNameTool(db_session)
        self.user_select_product_tool = UserSelectProductTool(db_session)
        self.get_inventory_tool = GetProductInventoryTool(db_session)
        self.increment_inventory_tool = IncrementInventoryTool(db_session)
        self.decrement_inventory_tool = DecrementInventoryTool(db_session)
        
        # Initialize the agent
        self.agent = ToolCallingAgent(
            tools=[
                self.create_product_tool,
                self.get_product_tool,
                self.update_product_tool,
                self.fetch_product_by_name_tool,
                self.user_select_product_tool,
                self.get_inventory_tool,
                self.increment_inventory_tool,
                self.decrement_inventory_tool,
            ],
            model=model,
            max_steps=5,
            name="products_agent",
            description="Manages product and inventory operations. Can create, retrieve, update, delete products and manage inventory levels.",
        )
    
    def process(self, message: str, user_id: str = None) -> str:
        """Process a product management request.
        
        Args:
            message: The user's product management request.
            user_id: Optional user identifier.
            
        Returns:
            The agent's response with operation result.
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
