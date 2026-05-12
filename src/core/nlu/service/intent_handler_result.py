from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class IntentHandlerResult:
    """Outcome from an intent handler; http_status 200 means fulfilled (terminal success)."""

    message: str
    http_status: Optional[int] = None
