from smolagents.tools import Tool
from typing import Optional
from sqlalchemy.orm import Session
import json
from core.product.service.product_service import ProductService


class UserSelectProductTool(Tool):
    """Tool for user to select a specific product from search results."""
    
    name = "product_user_select_tool"
    description = (
        "Confirm and select a specific product by its product ID from search results. "
        "Use this after fetching products by name to let the user or agent select which product to use. "
        "Once selected, you can then fetch inventory details using product_inventory_get_tool. "
        "Returns the selected product's full details for verification before proceeding."
    )
    inputs = {
        "product_id": {
            "type": "string",
            "description": "The unique identifier (UUID) of the product to select from the search results.",
            "required": True
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
        self.service = ProductService(db_session) if db_session else None

    def forward(self, product_id: str) -> str:
        """Select a product by ID.
        
        Args:
            product_id: The product ID to select
            
        Returns:
            JSON string with confirmation and full product details
        """
        if not self.service:
            return json.dumps({"ok": False, "message": "Database session not initialized"})
        
        try:
            product_id = product_id.strip() if isinstance(product_id, str) else product_id
            
            # Fetch product through service
            product = self.service.get_product_by_id(product_id)
            
            if product:
                return json.dumps({
                    "ok": True,
                    "message": f"Product selected: {product.name}",
                    "selection_confirmed": True,
                    "product": {
                        "product_id": str(product.product_id),
                        "inventory_id": product.inventory_id,
                        "name": product.name,
                        "description": product.description,
                        "category": product.category,
                        "brand": product.brand,
                        "barcode": product.barcode,
                        "tags": product.tags,
                        "created_at": product.created_at.isoformat() if product.created_at else None,
                        "updated_at": product.updated_at.isoformat() if product.updated_at else None
                    },
                    "next_steps": [
                        "Use product_inventory_get_tool with this product_id to fetch inventory details",
                        "Use product_update_tool to modify product information if needed",
                        "Use other product tools as required"
                    ]
                })
            else:
                return json.dumps({
                    "ok": False,
                    "message": f"Product with ID {product_id} not found",
                    "selection_confirmed": False
                })
                
        except ValueError as e:
            return json.dumps({"ok": False, "message": f"Invalid product ID format: {str(e)}"})
        except Exception as e:
            return json.dumps({"ok": False, "message": f"Error selecting product: {str(e)}"})
