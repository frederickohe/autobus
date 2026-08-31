"""Business pricing currency. Defaults to GHS for Ghana-based merchants."""

from __future__ import annotations

from typing import Any, Iterable, Optional, Sequence, Tuple

DEFAULT_CURRENCY = "GHS"

# code, display name, symbol
SUPPORTED_CURRENCIES: Tuple[Tuple[str, str, str], ...] = (
    ("GHS", "Ghanaian Cedi", "₵"),
    ("USD", "US Dollar", "$"),
    ("NGN", "Nigerian Naira", "₦"),
    ("XOF", "West African CFA", "CFA"),
    ("EUR", "Euro", "€"),
    ("GBP", "British Pound", "£"),
)

_SUPPORTED_CODES = {code for code, _, _ in SUPPORTED_CURRENCIES}


def normalize_currency_code(value: Optional[Any]) -> str:
    code = str(value or "").strip().upper()
    if code in _SUPPORTED_CODES:
        return code
    return DEFAULT_CURRENCY


def currency_symbol(code: Optional[str]) -> str:
    wanted = normalize_currency_code(code)
    for item_code, _, symbol in SUPPORTED_CURRENCIES:
        if item_code == wanted:
            return symbol
    return "₵"


def currency_label(code: Optional[str]) -> str:
    wanted = normalize_currency_code(code)
    for item_code, name, symbol in SUPPORTED_CURRENCIES:
        if item_code == wanted:
            return f"{item_code} ({symbol}) — {name}"
    return "GHS (₵) — Ghanaian Cedi"


def format_money(amount: Any, currency: Optional[str] = None) -> str:
    code = normalize_currency_code(currency)
    if amount is None:
        return code
    text = str(amount).strip()
    return f"{code} {text}" if text else code


def currency_from_user(user: Any) -> str:
    return normalize_currency_code(getattr(user, "currency_code", None))


def currency_from_user_data(user_data: Optional[dict]) -> str:
    if not user_data:
        return DEFAULT_CURRENCY
    return normalize_currency_code(user_data.get("currency_code"))


def currency_prompt_rule(code: Optional[str] = None) -> str:
    wanted = normalize_currency_code(code)
    symbol = currency_symbol(wanted)
    extra = ""
    if wanted != "USD":
        extra = " Never use $ or USD unless a customer explicitly asks about US dollars."
    return (
        f"Quote every price in {wanted} ({symbol}). "
        f"Do not invent a different currency.{extra}"
    )


def supported_currency_codes() -> Sequence[str]:
    return [code for code, _, _ in SUPPORTED_CURRENCIES]


def iter_currencies() -> Iterable[Tuple[str, str, str]]:
    return SUPPORTED_CURRENCIES
