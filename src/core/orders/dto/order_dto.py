"""
Order DTOs - Re-exporting from separate modules for backwards compatibility
"""
from .order_response_dto import OrderResponseDTO
from .order_create_dto import OrderCreateDTO
from .order_update_dto import OrderUpdateDTO

# Aliases for backwards compatibility
OrderResponse = OrderResponseDTO
OrderCreateRequest = OrderCreateDTO
OrderUpdate = OrderUpdateDTO

__all__ = [
    'OrderResponseDTO',
    'OrderCreateDTO',
    'OrderUpdateDTO',
    'OrderResponse',
    'OrderCreateRequest',
    'OrderUpdate',
]

