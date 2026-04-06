from smolagents.tools import Tool
from typing import Optional, Literal
from sqlalchemy.orm import Session
import json
from core.product.service.product_service import ProductService


class DecrementInventoryTool(Tool):
    """Tool for decrementing inventory quantities."""
    
    name = "inventory_decrement_tool"
    description = (
        "Decrement (decrease) a specific quantity field in an inventory record. "
        "Use this when removing stock, completing orders, or correcting inventory. "
        "Allows decrementing: quantity_on_hand, quantity_reserved, quantity_in_transit, "
        "quantity_on_order, or quantity_backordered. "
        "Prevents values from going below zero."
    )
    inputs = {
        "inventory_id": {
            "type": "string",
            "description": "The unique identifier (UUID) of the inventory record to update.",
            "required": True
        },
        "quantity_type": {
            "type": "string",
            "description": "Which quantity field to decrement: 'on_hand', 'reserved', 'in_transit', 'on_order', or 'backordered'.",
            "required": True
        },
        "amount": {
            "type": "number",
            "description": "The amount to decrement by (must be positive). For 'on_hand', this represents stock sold or removed.",
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
        self.quantity_fields = {
            "on_hand": "quantity_on_hand",
            "reserved": "quantity_reserved",
            "in_transit": "quantity_in_transit",
            "on_order": "quantity_on_order",
            "backordered": "quantity_backordered"
        }

    def forward(
        self,
        inventory_id: str,
        quantity_type: str,
        amount: float
    ) -> str:
        """Decrement an inventory quantity.
        
        Args:
            inventory_id: The inventory ID to update
            quantity_type: Type of quantity to decrement
            amount: Amount to decrement by
            
        Returns:
            JSON string with success/error information and updated values
        """
        if not self.service:
            return json.dumps({"ok": False, "message": "Database session not initialized"})
        
        try:
            inventory_id = inventory_id.strip() if isinstance(inventory_id, str) else inventory_id
            quantity_type = quantity_type.strip().lower() if isinstance(quantity_type, str) else quantity_type
            amount = float(amount)
            
            if amount <= 0:
                return json.dumps({"ok": False, "message": "Amount must be positive"})
            
            if quantity_type not in self.quantity_fields:
                return json.dumps({
                    "ok": False,
                    "message": f"Invalid quantity_type. Must be one of: {', '.join(self.quantity_fields.keys())}"
                })
            
            # Get inventory
            inventory = self.service.get_inventory_by_id(inventory_id)
            if not inventory:
                return json.dumps({"ok": False, "message": f"Inventory with ID {inventory_id} not found"})
            
            # Get the field to update
            field_name = self.quantity_fields[quantity_type]
            old_value = getattr(inventory, field_name)
            
            # Calculate new value
            decrement_amount = int(amount) if amount == int(amount) else amount
            new_value = old_value - decrement_amount
            
            # Prevent negative values
            if new_value < 0:
                return json.dumps({
                    "ok": False,
                    "message": f"Cannot decrement {quantity_type} by {amount}. Current value is {old_value}, would result in negative value.",
                    "current_value": old_value,
                    "requested_decrement": amount
                })
            
            # Update the inventory using the service
            from core.product.dto.inventory_update_dto import InventoryUpdateDTO
            update_data = InventoryUpdateDTO()
            setattr(update_data, field_name, new_value)
            
            success, updated_inv, message = self.service.update_inventory(inventory_id, update_data)
            
            if success:
                final_value = getattr(updated_inv, field_name)
                return json.dumps({
                    "ok": True,
                    "message": f"Inventory {quantity_type} decremented successfully",
                    "inventory_id": str(updated_inv.inventory_id),
                    "quantity_type": quantity_type,
                    "old_value": old_value,
                    "decrement_amount": amount,
                    "new_value": final_value,
                    "updated_at": updated_inv.updated_at.isoformat() if updated_inv.updated_at else None
                })
            else:
                return json.dumps({"ok": False, "message": message or "Failed to decrement inventory"})
                
        except ValueError as e:
            return json.dumps({"ok": False, "message": f"Invalid input: {str(e)}"})
        except Exception as e:
            return json.dumps({"ok": False, "message": f"Error decrementing inventory: {str(e)}"})
