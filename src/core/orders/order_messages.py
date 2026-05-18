"""User-facing order messages."""

OUT_OF_STOCK_ICON = "❌"


def format_out_of_stock_notice(item_name: str) -> str:
    """Notice when the ordered item is not listed in the merchant catalog."""
    display_name = (item_name or "This item").strip() or "This item"
    return (
        f"{OUT_OF_STOCK_ICON} Not in stock\n"
        f'"{display_name}" is not available in our catalog right now.\n'
        "Your order has still been placed — customer service will get back to you soon."
    )
