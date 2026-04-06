from smolagents.tools import Tool
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
import json
from core.product.service.product_service import ProductService
from core.product.dto.product_update_dto import ProductUpdateDTO


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
            sanitized[key] = value.strip() if value else value
        else:
            sanitized[key] = value
    return sanitized


class UpdateProductTool(Tool):
    """Tool for updating an existing product."""
    
    name = "product_update_tool"
    description = (
        "Update an existing product's information. "
        "You can update any combination of fields: name, description, category, brand, "
        "barcode, tags, and attributes. "
        "Only provided fields will be updated; other fields remain unchanged. "
        "Use this to modify product details."
    )
    inputs = {
        "product_id": {
            "type": "string",
            "description": "The unique identifier (UUID) of the product to update (required).",
            "required": True
        },
        "name": {
            "type": "string",
            "description": "Updated product name (1-255 characters).",
            "required": False,
            "nullable": True
        },
        "description": {
            "type": "string",
            "description": "Updated product description.",
            "required": False,
            "nullable": True
        },
        "category": {
            "type": "string",
            "description": "Updated product category.",
            "required": False,
            "nullable": True
        },
        "brand": {
            "type": "string",
            "description": "Updated brand name.",
            "required": False,
            "nullable": True
        },
        "barcode": {
            "type": "string",
            "description": "Updated barcode (must be unique if changed).",
            "required": False,
            "nullable": True
        },
        "tags": {
            "type": "array",
            "description": "Updated list of tags.",
            "required": False,
            "nullable": True
        },
        "attributes": {
            "type": "object",
            "description": "Updated product attributes as a JSON object.",
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
        product_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        category: Optional[str] = None,
        brand: Optional[str] = None,
        barcode: Optional[str] = None,
        tags: Optional[list] = None,
        attributes: Optional[dict] = None
    ) -> str:
        """Update a product.
        
        Args:
            product_id: The product ID to update
            name: Updated product name
            description: Updated description
            category: Updated category
            brand: Updated brand
            barcode: Updated barcode
            tags: Updated tags
            attributes: Updated attributes
            
        Returns:
            JSON string with success/error information and updated product details
        """
        if not self.service:
            return json.dumps({"ok": False, "message": "Database session not initialized"})
        
        try:
            product_id = product_id.strip() if isinstance(product_id, str) else product_id
            
            # Sanitize string inputs
            update_params = {}
            if name is not None:
                update_params["name"] = name.strip() if isinstance(name, str) else name
            if description is not None:
                update_params["description"] = description.strip() if isinstance(description, str) else description
            if category is not None:
                update_params["category"] = category.strip() if isinstance(category, str) else category
            if brand is not None:
                update_params["brand"] = brand.strip() if isinstance(brand, str) else brand
            if barcode is not None:
                update_params["barcode"] = barcode.strip() if isinstance(barcode, str) else barcode
            if tags is not None:
                update_params["tags"] = tags
            if attributes is not None:
                update_params["attributes"] = attributes
            
            # Create DTO with only provided fields
            product_data = ProductUpdateDTO(**update_params)
            
            # Update product through service
            result = self.service.update_product(product_id, product_data)
            
            # Handle tuples returned from service (success, product, message)
            if isinstance(result, tuple):
                success, product, message = result
                if success and product:
                    return json.dumps({
                        "ok": True,
                        "message": f"Product {product_id} updated successfully",
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
                            "updated_at": product.updated_at.isoformat() if product.updated_at else None
                        }
                    })
                else:
                    return json.dumps({"ok": False, "message": message or "Failed to update product"})
            else:
                return json.dumps({"ok": False, "message": "Unexpected response from service"})
                
        except ValueError as e:
            return json.dumps({"ok": False, "message": f"Validation error: {str(e)}"})
        except Exception as e:
            return json.dumps({"ok": False, "message": f"Error updating product: {str(e)}"})
