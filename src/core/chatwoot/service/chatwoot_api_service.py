import hashlib
import os
from typing import Any, Dict, Optional, Tuple

import httpx


class ChatwootAPIError(RuntimeError):
    pass


class ChatwootClient:
    """
    Minimal Chatwoot Platform API client for provisioning:
    - POST /platform/api/v1/accounts
    - POST /platform/api/v1/users
    - POST /platform/api/v1/accounts/{account_id}/account_users
    """

    def __init__(self, base_url: str, platform_api_token: str):
        self.base_url = base_url.rstrip("/")
        self.platform_api_token = platform_api_token.strip()

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _headers(self) -> Dict[str, str]:
        return {
            "api_access_token": self.platform_api_token,
            "Content-Type": "application/json",
        }

    async def create_account(
        self,
        *,
        name: str,
        support_email: Optional[str] = None,
        locale: str = "en",
        domain: Optional[str] = None,
        status: str = "active",
        timeout_s: float = 20.0,
    ) -> int:
        async with httpx.AsyncClient(timeout=timeout_s, follow_redirects=True) as client:
            payload: Dict[str, Any] = {"name": name, "locale": locale, "status": status}
            if support_email:
                payload["support_email"] = support_email
            if domain:
                payload["domain"] = domain

            res = await client.post(
                self._url("/platform/api/v1/accounts"),
                headers=self._headers(),
                json=payload,
            )
            if res.status_code >= 400:
                raise ChatwootAPIError(
                    f"Chatwoot create account failed ({res.status_code}): {res.text}"
                )

            data = res.json() if res.text.strip() else {}
            account_id = data.get("id")
            if account_id is None:
                raise ChatwootAPIError("Chatwoot create account response missing 'id'")
            return int(account_id)

    async def create_user(
        self,
        *,
        name: str,
        email: str,
        password: str,
        display_name: Optional[str] = None,
        timeout_s: float = 20.0,
    ) -> Tuple[int, str]:
        async with httpx.AsyncClient(timeout=timeout_s, follow_redirects=True) as client:
            payload: Dict[str, Any] = {
                "name": name,
                "email": email,
                "password": password,
            }
            if display_name:
                payload["display_name"] = display_name

            res = await client.post(
                self._url("/platform/api/v1/users"),
                headers=self._headers(),
                json=payload,
            )
            if res.status_code >= 400:
                raise ChatwootAPIError(
                    f"Chatwoot create user failed ({res.status_code}): {res.text}"
                )

            data = res.json() if res.text.strip() else {}
            user_id = data.get("id")
            access_token = data.get("access_token")
            if user_id is None or not access_token:
                raise ChatwootAPIError(
                    "Chatwoot create user response missing 'id' or 'access_token'"
                )
            return int(user_id), str(access_token)

    async def add_user_to_account(
        self,
        *,
        account_id: int,
        user_id: int,
        role: str = "administrator",
        timeout_s: float = 20.0,
    ) -> None:
        async with httpx.AsyncClient(timeout=timeout_s, follow_redirects=True) as client:
            res = await client.post(
                self._url(f"/platform/api/v1/accounts/{int(account_id)}/account_users"),
                headers=self._headers(),
                json={"user_id": int(user_id), "role": role},
            )
            if res.status_code >= 400:
                raise ChatwootAPIError(
                    f"Chatwoot add account user failed ({res.status_code}): {res.text}"
                )

    async def provision_account_and_user(
        self,
        *,
        account_name: str,
        email: str,
        name: str,
        password: str,
        support_email: Optional[str] = None,
        domain: Optional[str] = None,
        role: str = "administrator",
        timeout_s: float = 20.0,
    ) -> Tuple[int, int, str]:
        account_id = await self.create_account(
            name=account_name,
            support_email=support_email or email,
            domain=domain,
            timeout_s=timeout_s,
        )
        user_id, access_token = await self.create_user(
            name=name,
            email=email,
            password=password,
            timeout_s=timeout_s,
        )
        await self.add_user_to_account(
            account_id=account_id,
            user_id=user_id,
            role=role,
            timeout_s=timeout_s,
        )
        return account_id, user_id, access_token


def chatwoot_enabled() -> bool:
    return bool(os.getenv("CHATWOOT_BASE_URL", "").strip()) and bool(
        os.getenv("CHATWOOT_PLATFORM_API_TOKEN", "").strip()
    )


def derive_chatwoot_password(*, user_id: str, email: str, autobus_password_hash: str) -> str:
    """
    Deterministically derive a Chatwoot password without storing it.
    """
    seed = f"{user_id}|{email.lower()}|{autobus_password_hash}"
    # Ensure the password meets the documented requirement: upper/lower/number/special.
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return f"Aa1!{digest}"  # length ~ 68, deterministic and policy-compliant

