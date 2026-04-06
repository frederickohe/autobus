"""Product tools for agent interactions."""

from .product_create import CreateProductTool
from .product_get import GetProductTool
from .product_update import UpdateProductTool
from .product_fetch_by_name import FetchProductByNameTool
from .product_user_select import UserSelectProductTool
from .product_inventory_get import GetProductInventoryTool
from .inventory_increment import IncrementInventoryTool
from .inventory_decrement import DecrementInventoryTool

__all__ = [
    "CreateProductTool",
    "GetProductTool",
    "UpdateProductTool",
    "FetchProductByNameTool",
    "UserSelectProductTool",
    "GetProductInventoryTool",
    "IncrementInventoryTool",
    "DecrementInventoryTool",
]
