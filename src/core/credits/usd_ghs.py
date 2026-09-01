"""Convert catalog USD list prices to GHS for Paystack.

Packs are quoted in USD so Android/web match the App Store dollar prices.
Paystack (Ghana) is charged in cedis at the current USD/GHS rate.
"""

from __future__ import annotations

import logging
import time
from typing import Optional, Tuple

import httpx

from config import settings

logger = logging.getLogger(__name__)

_CACHE_TTL_SECONDS = 3600
_cached_rate: Optional[float] = None
_cached_at: float = 0.0

_RATE_URLS = (
    "https://open.er-api.com/v6/latest/USD",
    "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/usd.min.json",
)


def _rate_from_payload(data: object) -> Optional[float]:
    if not isinstance(data, dict):
        return None
    rates = data.get("rates")
    if isinstance(rates, dict) and rates.get("GHS") is not None:
        return float(rates["GHS"])
    usd = data.get("usd")
    if isinstance(usd, dict) and usd.get("ghs") is not None:
        return float(usd["ghs"])
    return None


async def get_usd_ghs_rate() -> float:
    """Live USD→GHS rate, cached for an hour. Optional env USD_GHS_RATE overrides."""
    global _cached_rate, _cached_at
    configured = float(getattr(settings, "USD_GHS_RATE", 0) or 0)
    if configured > 0:
        return configured

    now = time.monotonic()
    if _cached_rate and _cached_rate > 0 and (now - _cached_at) < _CACHE_TTL_SECONDS:
        return _cached_rate

    async with httpx.AsyncClient(timeout=8.0) as client:
        for url in _RATE_URLS:
            try:
                response = await client.get(url)
                response.raise_for_status()
                rate = _rate_from_payload(response.json())
                if rate and rate > 0:
                    _cached_rate = rate
                    _cached_at = now
                    return rate
            except Exception as exc:
                logger.warning("USD/GHS rate fetch failed from %s: %s", url, exc)

    if _cached_rate and _cached_rate > 0:
        return _cached_rate
    raise RuntimeError("Could not load a USD to GHS exchange rate")


async def usd_to_ghs(usd: float) -> Tuple[float, float]:
    """Return (ghs major units, usd_ghs_rate) for a USD list price."""
    rate = await get_usd_ghs_rate()
    ghs = round(float(usd) * rate, 2)
    if ghs <= 0:
        raise RuntimeError("Converted GHS amount is invalid")
    return ghs, rate
