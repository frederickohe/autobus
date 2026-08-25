"""Response DTO for saving a customer from a received order."""
from pydantic import BaseModel

from core.customers.dto.customer_dto import CustomerResponse
from core.orders.dto.order_response_dto import OrderResponseDTO


class SaveCustomerFromOrderResponse(BaseModel):
    created: bool
    already_saved: bool = False
    message: str
    customer: CustomerResponse
    order: OrderResponseDTO
