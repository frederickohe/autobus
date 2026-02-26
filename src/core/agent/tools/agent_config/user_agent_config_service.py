from typing import Any, Dict, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from core.user.model.User import User
from core.agent.agent_params import AGENT_REQUIRED_PARAMS


class AgentConfigService:
    def __init__(self, db: Session):
        self.db = db

    # ----- helpers -------------------------------------------------------
    def _get_user(self, user_id: str) -> Optional[User]:
        return self.db.query(User).filter(User.phone == user_id).first()

    def _validate_params(
        self, agent_name: str, params: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """Return (ok, message) for required‑key validation."""
        required = AGENT_REQUIRED_PARAMS.get(agent_name, [])
        missing = [k for k in required if k not in params or params.get(k) in (None, "")]
        if missing:
            return False, f"missing required parameters: {', '.join(missing)}"
        return True, None

    # ----- public API ----------------------------------------------------
    def create_or_update_agent(
        self,
        user_id: str,
        agent_name: str,
        params: Dict[str, Any],
        *,
        status: str = "active",
        **metadata: Any,
    ) -> Dict[str, Any]:
        """
        Create a new agent entry or update an existing one.

        The `params` dict is stored under the `params` key of the agent
        configuration; any additional keyword arguments are merged in as
        top‑level metadata (status, description, …).

        The method runs a simple required‑parameter check and commits the
        transaction before returning.
        """
        user = self._get_user(user_id)
        if not user:
            return {"ok": False, "message": "user not found"}

        ok, msg = self._validate_params(agent_name, params)
        if not ok:
            return {"ok": False, "message": msg}

        current = user.get_agent(agent_name) or {}
        current_params = current.get("params", {})
        current_params.update(params)
        current["params"] = current_params
        current.update(metadata)
        current.setdefault("status", status)

        user.set_agent(agent_name, current)
        flag_modified(user, "agents")
        self.db.add(user)
        self.db.commit()

        return {"ok": True, "agent": current}

    def get_agent(self, user_id: str, agent_name: str) -> Dict[str, Any]:
        user = self._get_user(user_id)
        if not user:
            return {"ok": False, "message": "user not found"}
        agent = user.get_agent(agent_name)
        if agent is None:
            return {"ok": False, "message": "agent not configured"}
        return {"ok": True, "agent": agent}

    def list_agents(self, user_id: str) -> Dict[str, Any]:
        user = self._get_user(user_id)
        if not user:
            return {"ok": False, "message": "user not found"}
        return {"ok": True, "agents": user.list_agents()}

    def delete_agent(self, user_id: str, agent_name: str) -> Dict[str, Any]:
        user = self._get_user(user_id)
        if not user:
            return {"ok": False, "message": "user not found"}
        if agent_name not in (user.agents or {}):
            return {"ok": False, "message": "agent not configured"}
        user.remove_agent(agent_name)
        flag_modified(user, "agents")
        self.db.add(user)
        self.db.commit()
        return {"ok": True}