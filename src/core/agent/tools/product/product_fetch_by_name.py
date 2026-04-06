from smolagents.tools import Tool
from typing import Optional
from sqlalchemy.orm import Session
import json
from core.product.service.product_service import ProductService


class FetchProductByNameTool(Tool):
    """Tool for searching products by name."""
    
    name = "product_fetch_by_name_tool"
    description = (
        "Search for products by name using partial matching (case-insensitive). "
        "Returns a list of products matching the search term. "
        "Use this to find products when the exact ID is not known, "
        "then use product_user_select_tool to let the user choose which product. "
        "Useful for inventory lookups across multiple products with similar names."
    )
    inputs = {
        "name": {
            "type": "string",
            "description": "The product name or partial name to search for (e.g., 'wireless headphones', 'headphones').",
            "required": True
        },
        "skip": {
            "type": "integer",
            "description": "Number of results to skip for pagination (default: 0).",
            "required": False,
            "nullable": True
        },
        "limit": {
            "type": "integer",
            "description": "Maximum number of results to return (default: 100).",
            "required": False,
            "nullable": True
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

    def forward(
        self,
        name: str,
        skip: int = 0,
        limit: int = 100
    ) -> str:
        """Search for products by name.
        
        Args:
            name: Product name or partial name to search
            skip: Number of results to skip
            limit: Maximum results to return
            
        Returns:
            JSON string with list of matching products
        """
        if not self.service:
            return json.dumps({"ok": False, "message": "Database session not initialized"})
        
        try:
            name = name.strip() if isinstance(name, str) else name
            
            if not name:
                return json.dumps({"ok": False, "message": "Product name cannot be empty"})
            
            # Fetch products by name through service
            products = self.service.get_product_by_name(name, skip=skip, limit=limit)
            
            if products:
                product_list = []
                for product in products:
                    product_list.append({
                        "product_id": str(product.product_id),
                        "inventory_id": product.inventory_id,
                        "name": product.name,
                        "description": product.description,
                        "category": product.category,
                        "brand": product.brand,
                        "barcode": product.barcode,
                        "created_at": product.created_at.isoformat() if product.created_at else None
                    })
                
                return json.dumps({
                    "ok": True,
                    "message": f"Found {len(product_list)} product(s) matching '{name}'",
                    "count": len(product_list),
                    "products": product_list
                })
            else:
                return json.dumps({
                    "ok": False,
                    "message": f"No products found matching '{name}'",
                    "count": 0,
                    "products": []
                })
                
        except Exception as e:
            return json.dumps({"ok": False, "message": f"Error searching products: {str(e)}"})
