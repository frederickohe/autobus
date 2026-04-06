"""
Product DTOs - Re-exporting from separate modules for backwards compatibility
"""
from .product_response_dto import ProductResponseDTO
from .product_create_dto import ProductCreateDTO
from .product_update_dto import ProductUpdateDTO
from .inventory_response_dto import InventoryResponseDTO
from .inventory_create_dto import InventoryCreateDTO
from .inventory_update_dto import InventoryUpdateDTO

# Aliases for backwards compatibility
ProductResponse = ProductResponseDTO
ProductCreateRequest = ProductCreateDTO
ProductUpdate = ProductUpdateDTO
InventoryResponse = InventoryResponseDTO
InventoryCreateRequest = InventoryCreateDTO
InventoryUpdate = InventoryUpdateDTO

__all__ = [
    'ProductResponseDTO',
    'ProductCreateDTO',
    'ProductUpdateDTO',
    'InventoryResponseDTO',
    'InventoryCreateDTO',
    'InventoryUpdateDTO',
    'ProductResponse',
    'ProductCreateRequest',
    'ProductUpdate',
    'InventoryResponse',
    'InventoryCreateRequest',
    'InventoryUpdate',
]

