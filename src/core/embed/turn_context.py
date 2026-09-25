"""Request-scoped context so the shop engine can tag embed orders without a global flag."""
from contextvars import ContextVar
from typing import Any, Dict, List, Optional, Tuple

_info: ContextVar[Optional[Dict[str, Any]]] = ContextVar("embed_turn_info", default=None)
_actions: ContextVar[Optional[List[Dict[str, Any]]]] = ContextVar("embed_turn_actions", default=None)


def begin_embed_turn(info: Dict[str, Any]) -> Tuple[Any, Any]:
    return _info.set(dict(info)), _actions.set([])


def embed_turn() -> Optional[Dict[str, Any]]:
    return _info.get()


def record_embed_action(action: Dict[str, Any]) -> None:
    bucket = _actions.get()
    if bucket is not None:
        bucket.append(action)


def end_embed_turn(tokens: Tuple[Any, Any]) -> List[Dict[str, Any]]:
    actions = list(_actions.get() or [])
    _info.reset(tokens[0])
    _actions.reset(tokens[1])
    return actions
