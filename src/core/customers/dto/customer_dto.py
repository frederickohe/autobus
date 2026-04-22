from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class CustomerCreateRequest(BaseModel):
    """Request model for creating/updating a customer."""
    name: str
    customer_number: str
    network: Optional[str] = None  # Auto-detected if not provided
    bank_code: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "name": "John Agyeman",
                "customer_number": "0550748724",
                "network": "MTN",
                "bank_code": None
            }
        }


class CustomerResponse(BaseModel):
    """Response model for customer."""
    id: int
    name: str
    customer_number: str
    network: str
    bank_code: Optional[str]
    account_type: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @classmethod
    def from_customer(cls, customer):
        """Convert Customer model to response DTO."""
        account_type_value = customer.account_type
        if hasattr(account_type_value, "value"):
            account_type_value = account_type_value.value
        elif isinstance(account_type_value, str):
            account_type_value = account_type_value.lower()

        return cls(
            id=customer.id,
            name=customer.name,
            customer_number=customer.customer_number,
            network=customer.network,
            bank_code=customer.bank_code,
            account_type=account_type_value,
            is_active=customer.is_active,
            created_at=customer.created_at,
            updated_at=customer.updated_at
        )
