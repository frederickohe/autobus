"""Decide what a customer photo means for the shop conversation.

Kept separate from the database so the rules can be tested on their own.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence


@dataclass
class MatchHit:
    product_id: str
    name: str
    price: str
    image_url: str
    score: float


@dataclass
class MatchDecision:
    kind: str = "none"
    hits: List[MatchHit] = field(default_factory=list)

    @property
    def found(self) -> bool:
        return self.kind in {"exact", "related"} and bool(self.hits)


def photo_should_identify_product(user_message: str, catalog: Sequence) -> bool:
    """True when the photo is the thing the customer is asking about."""
    from core.nlu.service.customer_shop import (
        is_shop_thanks,
        looks_like_existing_order_question,
        looks_like_faq,
        looks_like_order_request,
        match_catalog_in_text,
    )

    text = user_message or ""
    if is_shop_thanks(text) or looks_like_existing_order_question(text):
        return False
    if looks_like_faq(text) and not looks_like_order_request(text):
        return False
    if match_catalog_in_text(text, catalog):
        return False
    return True


def customer_image_intent(
    user_message: str,
    catalog: Sequence,
    decision: Optional[MatchDecision],
) -> Optional[tuple]:
    """Turn a match into shop intent slots. None means leave the text intent alone."""
    if decision is None or not decision.found:
        return None
    if not photo_should_identify_product(user_message, catalog):
        return None

    from core.nlu.service.customer_shop import extract_quantity, looks_like_order_request

    if decision.kind == "exact":
        hit = decision.hits[0]
        if looks_like_order_request(user_message):
            slots = {
                "item_name": hit.name,
                "product_id": hit.product_id,
            }
            if hit.price:
                slots["unit_price"] = hit.price
            quantity = extract_quantity(user_message)
            if quantity:
                slots["quantity"] = str(quantity)
            return "create_order", slots, []
        return (
            "view_product",
            {"product_name": hit.name, "product_id": hit.product_id},
            [],
        )

    heading = (
        "This looks like the closest match to your photo:"
        if len(decision.hits) == 1
        else "These look closest to the photo you sent:"
    )
    return (
        "view_products",
        {
            "related_product_ids": ",".join(hit.product_id for hit in decision.hits),
            "image_match_heading": heading,
        },
        [],
    )
