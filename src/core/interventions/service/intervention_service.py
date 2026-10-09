from __future__ import annotations

import logging
from dataclasses import asdict
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from core.interventions.model.Intervention import Intervention
from core.notification.service.event_notification_service import EventNotificationService
from utilities.dbconfig import SessionLocal

logger = logging.getLogger(__name__)


class InterventionService:
    def __init__(self, db: Session):
        self.db = db

    def create_intervention(
        self,
        *,
        user_id: str,
        trigger: str,
        reason: Optional[str] = None,
        conversation_date: Optional[date] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Intervention:
        conv_date = conversation_date or date.today()

        # An open intervention for today is reused, and the owner is still texted.
        existing = (
            self.db.query(Intervention)
            .filter(
                Intervention.user_id == user_id,
                Intervention.conversation_date == conv_date,
                Intervention.status == "open",
            )
            .order_by(Intervention.created_at.desc())
            .first()
        )
        if existing:
            self._notify_owner(
                user_id=user_id,
                intervention_id=int(existing.id),
                trigger=trigger,
                reason=reason,
                conversation_date=conv_date,
            )
            return existing

        intervention = Intervention(
            user_id=user_id,
            conversation_date=conv_date,
            status="open",
            trigger=trigger,
            reason=reason,
            meta=metadata or {},
        )
        self.db.add(intervention)
        self.db.commit()
        self.db.refresh(intervention)

        self._notify_owner(
            user_id=user_id,
            intervention_id=int(intervention.id),
            trigger=trigger,
            reason=reason,
            conversation_date=conv_date,
        )
        return intervention

    def _notify_owner(
        self,
        *,
        user_id: str,
        intervention_id: int,
        trigger: str,
        reason: Optional[str],
        conversation_date: date,
    ) -> None:
        """Text the business owner. Failures stay in the log and do not block the chat."""
        try:
            notify_db = SessionLocal()
            try:
                EventNotificationService(notify_db).notify_intervention_active(
                    user_id=user_id,
                    intervention_id=intervention_id,
                    trigger=trigger,
                    reason=reason,
                    conversation_date=str(conversation_date),
                )
            finally:
                notify_db.close()
        except Exception:
            logger.exception(
                "[INTERVENTIONS] Failed to notify owner for intervention %s (%s)",
                intervention_id,
                user_id,
            )

    def close_intervention(self, *, intervention_id: int, user_id: str) -> Intervention:
        intervention = (
            self.db.query(Intervention)
            .filter(
                Intervention.id == int(intervention_id),
                or_(
                    Intervention.user_id == user_id,
                    Intervention.user_id.like(f"{user_id}:%"),
                ),
            )
            .first()
        )
        if not intervention:
            raise ValueError("Intervention not found")

        intervention.status = "closed"
        intervention.closed_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(intervention)
        return intervention

    def list_interventions(
        self,
        *,
        user_id: str,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[Intervention]:
        q = self.db.query(Intervention).filter(
            or_(
                Intervention.user_id == user_id,
                Intervention.user_id.like(f"{user_id}:%"),
            )
        )
        if status:
            q = q.filter(Intervention.status == status)
        return q.order_by(Intervention.created_at.desc()).limit(int(limit)).all()

    def get_intervention(self, *, intervention_id: int, user_id: str) -> Optional[Intervention]:
        return (
            self.db.query(Intervention)
            .filter(Intervention.id == int(intervention_id), Intervention.user_id == user_id)
            .first()
        )

