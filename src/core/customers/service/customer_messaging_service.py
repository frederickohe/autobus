import json
import logging
import os
import smtplib
import ssl
from datetime import datetime, timezone
from email.message import EmailMessage
from typing import Any, Dict, List, Optional

import redis
from sqlalchemy.orm import Session

from config import settings
from core.customers.dto.customer_dto import (
    CustomerMessageRecipientResult,
    CustomerMessageResponse,
)
from core.customers.service.customer_service import CustomerService
from core.customers.utility.network_detector import Network
from core.wirepick.service.wirepickservice import WirepickSMSService, WirepickSMSException

logger = logging.getLogger(__name__)

_SMS_NETWORKS = {Network.MTN, Network.VOD, Network.AIR}
_SENT_SMS_KEY_PREFIX = "sms:sent:"
_SENT_SMS_MAX = 100


class CustomerMessagingService:
    """Send custom SMS or email to saved customers by customer ID."""

    def __init__(self, db: Session, redis_client=None):
        self.db = db
        self.customer_service = CustomerService(db)
        self.sms_service = WirepickSMSService()
        self._redis_client = redis_client

    def send_sms(
        self,
        user_id: str,
        customer_ids: List[int],
        message: str,
    ) -> CustomerMessageResponse:
        customers_by_id = {
            c.id: c for c in self.customer_service.get_customers_by_ids(customer_ids, user_id)
        }
        results: List[CustomerMessageRecipientResult] = []

        for customer_id in customer_ids:
            customer = customers_by_id.get(customer_id)
            if not customer:
                results.append(
                    CustomerMessageRecipientResult(
                        customer_id=customer_id,
                        customer_name="",
                        success=False,
                        message="Customer not found or not accessible",
                    )
                )
                continue

            network_enum = getattr(Network, customer.network, None)
            if network_enum not in _SMS_NETWORKS:
                results.append(
                    CustomerMessageRecipientResult(
                        customer_id=customer.id,
                        customer_name=customer.name,
                        success=False,
                        message=(
                            f"SMS is only supported for mobile money customers "
                            f"(MTN, VOD, AIR). This customer uses network {customer.network}."
                        ),
                    )
                )
                continue

            phone = customer.customer_number
            try:
                sms_result = self.sms_service.send_sms(phone, message)
                if sms_result.get("success"):
                    self._record_sent_sms(
                        user_id,
                        phone=phone,
                        message=message,
                        status="Sent",
                    )
                    results.append(
                        CustomerMessageRecipientResult(
                            customer_id=customer.id,
                            customer_name=customer.name,
                            success=True,
                            message="SMS sent successfully",
                            destination=phone,
                        )
                    )
                else:
                    error = sms_result.get("error", "SMS provider error")
                    results.append(
                        CustomerMessageRecipientResult(
                            customer_id=customer.id,
                            customer_name=customer.name,
                            success=False,
                            message=f"Failed to send SMS: {error}",
                            destination=phone,
                        )
                    )
            except WirepickSMSException as exc:
                logger.error("Wirepick SMS error for customer %s: %s", customer.id, exc)
                results.append(
                    CustomerMessageRecipientResult(
                        customer_id=customer.id,
                        customer_name=customer.name,
                        success=False,
                        message="Failed to send SMS. Please try again later.",
                        destination=phone,
                    )
                )

        return self._build_response(results)

    def send_email(
        self,
        user_id: str,
        customer_ids: List[int],
        subject: str,
        body: str,
    ) -> CustomerMessageResponse:
        if not settings.ZEPTOMAIL_SMTP_PASSWORD:
            raise ValueError("Email service is not configured")

        sender_domain = os.getenv("ZEPTOMAIL_SENDER_DOMAIN", "useautobus.com").strip()
        from_email = settings.ZEPTOMAIL_FROM_EMAIL or f"no-reply@{sender_domain}"

        customers_by_id = {
            c.id: c for c in self.customer_service.get_customers_by_ids(customer_ids, user_id)
        }
        results: List[CustomerMessageRecipientResult] = []

        for customer_id in customer_ids:
            customer = customers_by_id.get(customer_id)
            if not customer:
                results.append(
                    CustomerMessageRecipientResult(
                        customer_id=customer_id,
                        customer_name="",
                        success=False,
                        message="Customer not found or not accessible",
                    )
                )
                continue

            if not customer.email:
                results.append(
                    CustomerMessageRecipientResult(
                        customer_id=customer.id,
                        customer_name=customer.name,
                        success=False,
                        message="Customer has no email address. Add an email when creating or updating the customer.",
                    )
                )
                continue

            to_email = customer.email.strip()
            try:
                sent = self._send_email(from_email, to_email, subject, body)
                if sent:
                    results.append(
                        CustomerMessageRecipientResult(
                            customer_id=customer.id,
                            customer_name=customer.name,
                            success=True,
                            message="Email sent successfully",
                            destination=to_email,
                        )
                    )
                else:
                    results.append(
                        CustomerMessageRecipientResult(
                            customer_id=customer.id,
                            customer_name=customer.name,
                            success=False,
                            message="Failed to send email",
                            destination=to_email,
                        )
                    )
            except Exception as exc:
                logger.error("Email send error for customer %s: %s", customer.id, exc)
                results.append(
                    CustomerMessageRecipientResult(
                        customer_id=customer.id,
                        customer_name=customer.name,
                        success=False,
                        message="Failed to send email. Please try again later.",
                        destination=to_email,
                    )
                )

        return self._build_response(results)

    def _redis(self):
        if self._redis_client is not None:
            return self._redis_client
        redis_password = os.getenv("REDIS_PASSWORD", "autobus098")
        self._redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "redis"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            password=redis_password if redis_password else None,
            db=0,
            decode_responses=True,
        )
        return self._redis_client

    def _history_user_id(self, user_id: str) -> Optional[str]:
        return self.customer_service._resolve_user_db_id(user_id) or (user_id or "").strip() or None

    def _record_sent_sms(
        self,
        user_id: str,
        *,
        phone: str,
        message: str,
        status: str = "Sent",
    ) -> None:
        """Append outbound SMS metadata for Sent SMS history (newest first)."""
        history_user_id = self._history_user_id(user_id)
        if not history_user_id:
            return
        try:
            payload = json.dumps(
                {
                    "phone": phone,
                    "message": message,
                    "sent_at": datetime.now(timezone.utc).isoformat(),
                    "status": status,
                }
            )
            key = f"{_SENT_SMS_KEY_PREFIX}{history_user_id}"
            client = self._redis()
            client.lpush(key, payload)
            client.ltrim(key, 0, _SENT_SMS_MAX - 1)
        except Exception as e:
            logger.warning("Could not record sent SMS for user %s: %s", user_id, e)

    def list_sent_sms_for_user(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Return recent SMS sent by this user through customer messaging (Redis-backed)."""
        if limit < 1:
            limit = 1
        if limit > 50:
            limit = 50
        history_user_id = self._history_user_id(user_id)
        if not history_user_id:
            return []
        key = f"{_SENT_SMS_KEY_PREFIX}{history_user_id}"
        try:
            raw = self._redis().lrange(key, 0, limit - 1)
        except Exception as e:
            logger.error("Redis error listing sent SMS for %s: %s", user_id, e)
            return []
        out: List[Dict[str, Any]] = []
        for row in raw or []:
            try:
                parsed = json.loads(row)
            except (json.JSONDecodeError, TypeError):
                continue
            if isinstance(parsed, dict):
                out.append(parsed)
        return out

    @staticmethod
    def _send_email(from_email: str, to_email: str, subject: str, body: str) -> bool:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = from_email
        msg["To"] = to_email
        msg.set_content(body)

        smtp_host = settings.ZEPTOMAIL_SMTP_HOST
        smtp_port = settings.ZEPTOMAIL_SMTP_PORT
        smtp_username = settings.ZEPTOMAIL_SMTP_USERNAME
        smtp_password = settings.ZEPTOMAIL_SMTP_PASSWORD

        if smtp_port == 465:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context, timeout=30) as server:
                server.login(smtp_username, smtp_password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
                server.starttls()
                server.login(smtp_username, smtp_password)
                server.send_message(msg)
        return True

    @staticmethod
    def _build_response(results: List[CustomerMessageRecipientResult]) -> CustomerMessageResponse:
        sent = sum(1 for r in results if r.success)
        failed = len(results) - sent
        return CustomerMessageResponse(
            total=len(results),
            sent=sent,
            failed=failed,
            results=results,
        )
