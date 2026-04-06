from smolagents.tools import Tool
from typing import Optional
from sqlalchemy.orm import Session
import json
from core.product.service.product_service import ProductService


class GetProductInventoryTool(Tool):
    """Tool for retrieving inventory details for a product."""
    
    name = "product_inventory_get_tool"
    description = (
        "Fetch complete inventory details for a specific product by its product ID. "
        "Returns all inventory records associated with the product, including stock levels, "
        "reorder points, locations, and stock forecasting metrics. "
        "Use this after identifying a product to get detailed inventory information. "
        "Useful for inventory queries like: 'How much stock do we have?', 'What's the reorder point?', etc."
    )
    inputs = {
        "product_id": {
            "type": "string",
            "description": "The unique identifier (UUID) of the product to get inventory for (required).",
            "required": True
        },
        "location": {
            "type": "string",
            "description": "Optional: Filter inventory by specific location (e.g., 'warehouse-a', 'store-1').",
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
        location: Optional[str] = None
    ) -> str:
        """Get inventory for a product.
        
        Args:
            product_id: The product ID (UUID)
            location: Optional location filter
            
        Returns:
            JSON string with inventory details and stock information
        """
        if not self.service:
            return json.dumps({"ok": False, "message": "Database session not initialized"})
        
        try:
            product_id = product_id.strip() if isinstance(product_id, str) else product_id
            location = location.strip() if isinstance(location, str) else location
            
            # First get the product to verify it exists
            product = self.service.get_product_by_id(product_id)
            if not product:
                return json.dumps({
                    "ok": False,
                    "message": f"Product with ID {product_id} not found"
                })
            
            # Fetch inventory through service
            inventory_records = self.service.get_product_inventory(product_id, location=location)
            
            if inventory_records:
                inventory_list = []
                total_on_hand = 0
                total_reserved = 0
                total_available = 0
                
                for inv in inventory_records:
                    available = inv.quantity_on_hand - inv.quantity_reserved
                    total_on_hand += inv.quantity_on_hand
                    total_reserved += inv.quantity_reserved
                    total_available += available
                    
                    inventory_list.append({
                        "inventory_id": str(inv.inventory_id),
                        "location": inv.location or "Default",
                        "name": inv.name,
                        "quantity_on_hand": inv.quantity_on_hand,
                        "quantity_reserved": inv.quantity_reserved,
                        "quantity_available": available,
                        "quantity_in_transit": inv.quantity_in_transit,
                        "quantity_on_order": inv.quantity_on_order,
                        "quantity_backordered": inv.quantity_backordered,
                        "min_stock_level": inv.min_stock_level,
                        "max_stock_level": inv.max_stock_level,
                        "reorder_point": inv.reorder_point,
                        "reorder_quantity": inv.reorder_quantity,
                        "optimal_stock_level": inv.optimal_stock_level,
                        "stockout_risk_score": inv.stockout_risk_score,
                        "days_of_inventory": inv.days_of_inventory,
                        "updated_at": inv.updated_at.isoformat() if inv.updated_at else None
                    })
                
                return json.dumps({
                    "ok": True,
                    "message": f"Found {len(inventory_list)} inventory record(s) for product '{product.name}'",
                    "product": {
                        "product_id": str(product.product_id),
                        "inventory_id": product.inventory_id,
                        "name": product.name,
                        "category": product.category,
                        "brand": product.brand
                    },
                    "summary": {
                        "total_quantity_on_hand": total_on_hand,
                        "total_quantity_reserved": total_reserved,
                        "total_quantity_available": total_available,
                        "number_of_locations": len(inventory_list)
                    },
                    "inventory_records": inventory_list
                })
            else:
                return json.dumps({
                    "ok": False,
                    "message": f"No inventory records found for product '{product.name}'",
                    "product": {
                        "product_id": str(product.product_id),
                        "name": product.name
                    },
                    "inventory_records": []
                })
                
        except ValueError as e:
            return json.dumps({"ok": False, "message": f"Invalid product ID format: {str(e)}"})
        except Exception as e:
            return json.dumps({"ok": False, "message": f"Error fetching inventory: {str(e)}"})
