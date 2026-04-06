from smolagents.tools import Tool
from typing import Optional
from sqlalchemy.orm import Session
import json
from core.product.service.product_service import ProductService


class GetProductTool(Tool):
    """Tool for retrieving a specific product by its ID."""
    
    name = "product_get_tool"
    description = (
        "Fetch a specific product by its product ID. "
        "Returns detailed information about the product including name, description, "
        "category, brand, barcode, tags, and attributes. "
        "Use this to retrieve product details for viewing or further operations."
    )
    inputs = {
        "product_id": {
            "type": "string",
            "description": "The unique identifier (UUID) of the product to retrieve (required).",
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
        """Retrieve a product by ID.
        
        Args:
            product_id: The product ID (UUID)
            
        Returns:
            JSON string with success/error information and product details
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
                    "message": "Product retrieved successfully",
                    "product": {
                        "product_id": str(product.product_id),
                        "inventory_id": product.inventory_id,
                        "name": product.name,
                        "description": product.description,
                        "category": product.category,
                        "brand": product.brand,
                        "barcode": product.barcode,
                        "tags": product.tags,
                        "attributes": product.attributes,
                        "created_at": product.created_at.isoformat() if product.created_at else None,
                        "updated_at": product.updated_at.isoformat() if product.updated_at else None,
                        "last_sold_at": product.last_sold_at.isoformat() if product.last_sold_at else None,
                        "last_ordered_at": product.last_ordered_at.isoformat() if product.last_ordered_at else None
                    }
                })
            else:
                return json.dumps({
                    "ok": False,
                    "message": f"Product with ID {product_id} not found"
                })
                
        except ValueError as e:
            return json.dumps({"ok": False, "message": f"Invalid product ID format: {str(e)}"})
        except Exception as e:
            return json.dumps({"ok": False, "message": f"Error fetching product: {str(e)}"})
