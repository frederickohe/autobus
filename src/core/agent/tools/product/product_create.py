from smolagents.tools import Tool
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
import json
from core.product.service.product_service import ProductService
from core.product.dto.product_create_dto import ProductCreateDTO


def _sanitize_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize parameters by stripping whitespace from string values.
    
    This fixes issues where LLMs might introduce unintended spaces or newlines
    in generated values.
    
    Args:
        params: Dictionary of parameters to sanitize
        
    Returns:
        Dictionary with whitespace stripped from string values
    """
    sanitized = {}
    for key, value in params.items():
        if isinstance(value, str):
            sanitized[key] = value.strip()
        else:
            sanitized[key] = value
    return sanitized


class CreateProductTool(Tool):
    """Tool for creating a new product."""
    
    name = "product_create_tool"
    description = (
        "Create a new product in the product catalog. "
        "Automatically generates an inventory ID from the product name and "
        "creates an associated inventory record with zero initial stock. "
        "Use this to add new products to the system."
    )
    inputs = {
        "name": {
            "type": "string",
            "description": "The name of the product (required, 1-255 characters).",
            "required": True
        },
        "description": {
            "type": "string",
            "description": "Detailed description of the product.",
            "required": False,
            "nullable": True
        },
        "category": {
            "type": "string",
            "description": "Product category (e.g., 'Electronics', 'Clothing').",
            "required": False,
            "nullable": True
        },
        "brand": {
            "type": "string",
            "description": "Brand name of the product.",
            "required": False,
            "nullable": True
        },
        "barcode": {
            "type": "string",
            "description": "UPC/EAN barcode for the product (must be unique if provided).",
            "required": False,
            "nullable": True
        },
        "tags": {
            "type": "array",
            "description": "List of tags for categorization and search (e.g., ['wireless', 'premium']).",
            "required": False,
            "nullable": True
        },
        "attributes": {
            "type": "object",
            "description": "Flexible JSON object for product-specific attributes (e.g., {'color': 'black', 'weight': '250g'}).",
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
        description: Optional[str] = None,
        category: Optional[str] = None,
        brand: Optional[str] = None,
        barcode: Optional[str] = None,
        tags: Optional[list] = None,
        attributes: Optional[dict] = None
    ) -> str:
        """Create a new product.
        
        Args:
            name: Product name
            description: Product description
            category: Product category
            brand: Brand name
            barcode: Product barcode
            tags: List of tags
            attributes: Product attributes
            
        Returns:
            JSON string with success/error information and product details
        """
        if not self.service:
            return json.dumps({"ok": False, "message": "Database session not initialized"})
        
        try:
            # Sanitize string inputs
            name = name.strip() if isinstance(name, str) else name
            description = description.strip() if isinstance(description, str) else description
            category = category.strip() if isinstance(category, str) else category
            brand = brand.strip() if isinstance(brand, str) else brand
            barcode = barcode.strip() if isinstance(barcode, str) else barcode
            
            # Create DTO
            product_data = ProductCreateDTO(
                name=name,
                description=description,
                category=category,
                brand=brand,
                barcode=barcode,
                tags=tags,
                attributes=attributes
            )
            
            # Create product through service
            result = self.service.create_product(product_data)
            
            # Handle tuples returned from service (success, product, message)
            if isinstance(result, tuple):
                success, product, message = result
                if success and product:
                    return json.dumps({
                        "ok": True,
                        "message": f"Product '{name}' created successfully",
                        "product": {
                            "product_id": str(product.product_id),
                            "inventory_id": product.inventory_id,
                            "name": product.name,
                            "description": product.description,
                            "category": product.category,
                            "brand": product.brand,
                            "barcode": product.barcode,
                            "tags": product.tags,
                            "attributes": product.attributes
                        }
                    })
                else:
                    return json.dumps({"ok": False, "message": message or "Failed to create product"})
            else:
                return json.dumps({"ok": False, "message": "Unexpected response from service"})
                
        except ValueError as e:
            return json.dumps({"ok": False, "message": f"Validation error: {str(e)}"})
        except Exception as e:
            return json.dumps({"ok": False, "message": f"Error creating product: {str(e)}"})
