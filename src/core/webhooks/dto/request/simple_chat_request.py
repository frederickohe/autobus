from typing import Optional

from pydantic import BaseModel, Field


class SimpleChatRequest(BaseModel):
    """JSON body for ``POST /api/v1/webhooks/start-dialog`` (non-Meta clients).

    Preferred shape — three fields:

    - ``customer_number``: end customer phone / channel identifier
    - ``company_number``: merchant account id (``users.id`` in Autobus)
    - ``message``: inbound text

    Legacy: ``userid`` + ``message`` (omit ``customer_number`` / ``company_number``).
    """

    customer_number: Optional[str] = Field(
        default=None,
        description="Customer phone or external channel id",
    )
    company_number: Optional[str] = Field(
        default=None,
        description="Merchant internal id (users.id); when set, conversation is scoped per merchant",
    )
    message: Optional[str] = Field(default=None, description="Inbound user message")
    userid: Optional[str] = Field(
        default=None,
        description="Legacy alias for customer_number",
    )
