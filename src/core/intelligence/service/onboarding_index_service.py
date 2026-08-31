"""Save signup onboarding answers and index them into Qdrant intelligence."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from core.intelligence.dto.onboarding_response import (
    OnboardingProfileResponse,
    OnboardingQuestion,
)
from core.rag.conversation_vector_client import ConversationVectorClient
from core.rag.document_indexer import index_extracted_text_for_user
from core.rag.sources import ONBOARDING_SOURCE
from core.rag.tenant import resolve_effective_rag_tenant_id
from core.user.model.User import User

logger = logging.getLogger(__name__)

ONBOARDING_OBJECT_KEY = "onboarding/business-profile"
ONBOARDING_FILE_NAME = "business-onboarding.txt"

ONBOARDING_QUESTIONS: List[OnboardingQuestion] = [
    OnboardingQuestion(
        id="business_name",
        prompt="What is your business name?",
        hint="The name customers should hear from your chatbot.",
        placeholder="e.g. Sunrise Bakery",
        multiline=False,
        required=True,
    ),
    OnboardingQuestion(
        id="business_description",
        prompt="Describe your business in one sentence.",
        hint="A short pitch the chatbot can use when someone asks what you do.",
        placeholder="e.g. We bake fresh sourdough and pastries for families in Accra.",
        multiline=True,
        required=True,
    ),
    OnboardingQuestion(
        id="target_customers",
        prompt="Who are your target customers?",
        hint="Who should the chatbot speak to — and who is a good fit?",
        placeholder="e.g. Busy professionals and households in Greater Accra.",
        multiline=True,
        required=True,
    ),
    OnboardingQuestion(
        id="products_services",
        prompt="What products or services do you offer?",
        hint="List the main things you sell or deliver.",
        placeholder="e.g. Sourdough loaves, croissants, custom cakes, catering.",
        multiline=True,
        required=True,
    ),
    OnboardingQuestion(
        id="industry",
        prompt="What industry or category are you in?",
        hint="Helps the chatbot use the right language for your market.",
        placeholder="e.g. Food and bakery, retail fashion, logistics",
        multiline=False,
        required=True,
    ),
    OnboardingQuestion(
        id="service_area",
        prompt="Where do you operate?",
        hint="City, neighborhood, delivery radius, or online only.",
        placeholder="e.g. Accra and Tema, plus nationwide delivery",
        multiline=False,
        required=True,
    ),
    OnboardingQuestion(
        id="differentiator",
        prompt="What makes your business unique?",
        hint="Why should a customer choose you over alternatives?",
        placeholder="e.g. Same-day delivery and naturally fermented bread.",
        multiline=True,
        required=True,
    ),
    OnboardingQuestion(
        id="chatbot_greeting",
        prompt="How should your chatbot greet customers?",
        hint="Optional. Leave blank to use a friendly default.",
        placeholder="e.g. Hi! Welcome to Sunrise Bakery — how can we help today?",
        multiline=True,
        required=False,
    ),
]

_QUESTION_BY_ID = {q.id: q for q in ONBOARDING_QUESTIONS}

_MIN_ANSWER_LEN = 2
_MAX_ANSWER_LEN = 2000


def question_catalog() -> List[OnboardingQuestion]:
    return list(ONBOARDING_QUESTIONS)


def stored_profile(user: User) -> Dict[str, Any]:
    raw = getattr(user, "onboarding_profile", None)
    return dict(raw) if isinstance(raw, dict) else {}


def format_onboarding_document(profile: Dict[str, Any], *, company: str = "") -> str:
    """Plain-text document written for both humans and Qdrant retrieval."""
    answers = _answers_from_profile(profile)
    name = answers.get("business_name") or company or "This business"
    description = answers.get("business_description") or ""
    customers = answers.get("target_customers") or ""
    offerings = answers.get("products_services") or ""
    industry = answers.get("industry") or ""
    area = answers.get("service_area") or ""
    unique = answers.get("differentiator") or ""
    greeting = answers.get("chatbot_greeting") or ""

    lines = [
        f"# Business profile for {name}",
        "",
        "This profile was provided by the business owner during onboarding.",
        "Use it to answer customer questions about the business even when no",
        "website or documents have been uploaded.",
        "",
        f"Business name: {name}",
    ]
    if description:
        lines.append(f"One-sentence description: {description}")
    if industry:
        lines.append(f"Industry: {industry}")
    if customers:
        lines.append(f"Target customers: {customers}")
    if offerings:
        lines.append(f"Products and services: {offerings}")
    if area:
        lines.append(f"Service area: {area}")
    if unique:
        lines.append(f"What makes us unique: {unique}")
    if greeting:
        lines.append(f"Preferred customer greeting: {greeting}")

    lines.extend(
        [
            "",
            "## Facts for customer questions",
            f"- We are {name}.",
        ]
    )
    if description:
        lines.append(f"- What we do: {description}")
    if offerings:
        lines.append(f"- We offer: {offerings}")
    if customers:
        lines.append(f"- We serve: {customers}")
    if area:
        lines.append(f"- We operate in: {area}")
    if unique:
        lines.append(f"- Why customers choose us: {unique}")
    if industry:
        lines.append(f"- Industry: {industry}")
    return "\n".join(lines).strip()


def format_onboarding_as_rag_context(
    profile: Optional[Dict[str, Any]], *, company: str = ""
) -> Optional[str]:
    if not isinstance(profile, dict) or not _answers_from_profile(profile):
        return None
    text = format_onboarding_document(profile, company=company)
    if not text:
        return None
    return f"- (onboarding | system | 1.000) {text}"


class OnboardingIndexService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_profile(self, user: User) -> OnboardingProfileResponse:
        profile = stored_profile(user)
        return OnboardingProfileResponse(
            completed=bool(getattr(user, "onboarding_completed", False)),
            profile=profile,
            questions=question_catalog(),
        )

    def submit(self, user: User, answers: Dict[str, Any]) -> OnboardingProfileResponse:
        db_user = self.db.query(User).filter(User.id == user.id).first()
        if not db_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        user = db_user
        cleaned = self._validate_answers(answers)
        now = datetime.now(timezone.utc).isoformat()
        existing = stored_profile(user)
        profile = {
            "answers": cleaned,
            "completed_at": now,
            "updated_at": now,
            "version": int(existing.get("version") or 0) + 1,
        }

        user.onboarding_profile = profile
        user.onboarding_completed = True
        flag_modified(user, "onboarding_profile")

        business_name = cleaned.get("business_name")
        if business_name:
            user.company = business_name
        service_area = cleaned.get("service_area")
        if service_area:
            user.location = service_area[:255]
        user.updated_at = datetime.now(timezone.utc)

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        indexed, rag_detail = self._replace_onboarding_vectors(user, profile)
        return OnboardingProfileResponse(
            completed=True,
            profile=profile,
            questions=question_catalog(),
            indexed_chunks=indexed,
            rag_detail=rag_detail,
        )

    def _validate_answers(self, answers: Dict[str, Any]) -> Dict[str, str]:
        if not isinstance(answers, dict) or not answers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please answer the onboarding questions.",
            )
        cleaned: Dict[str, str] = {}
        missing: List[str] = []
        for question in ONBOARDING_QUESTIONS:
            raw = answers.get(question.id)
            text = _clean_answer(raw)
            if not text:
                if question.required:
                    missing.append(question.prompt)
                continue
            if len(text) < _MIN_ANSWER_LEN:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Please give a fuller answer for: {question.prompt}",
                )
            if len(text) > _MAX_ANSWER_LEN:
                text = text[:_MAX_ANSWER_LEN].rstrip()
            cleaned[question.id] = text

        extra_ids = [k for k in answers.keys() if k not in _QUESTION_BY_ID]
        for extra_id in extra_ids:
            text = _clean_answer(answers.get(extra_id))
            if text:
                cleaned[str(extra_id)] = text[:_MAX_ANSWER_LEN]

        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please answer: " + "; ".join(missing),
            )
        return cleaned

    def refresh_from_user_profile(self, user: User) -> Optional[int]:
        """
        Keep Qdrant onboarding points in sync with Profile edits.

        Only the onboarding source is deleted and rewritten. Uploaded
        documents and websites are left untouched.
        """
        db_user = self.db.query(User).filter(User.id == user.id).first()
        if not db_user:
            return None
        user = db_user
        existing = stored_profile(user)
        answers = _answers_from_profile(existing)
        if not answers and not bool(getattr(user, "onboarding_completed", False)):
            return None

        if (user.company or "").strip():
            answers["business_name"] = (user.company or "").strip()
        if (user.location or "").strip():
            answers["service_area"] = (user.location or "").strip()
        if not answers:
            return None

        now = datetime.now(timezone.utc).isoformat()
        profile = {
            "answers": answers,
            "completed_at": existing.get("completed_at") or now,
            "updated_at": now,
            "version": int(existing.get("version") or 0) + 1,
        }
        user.onboarding_profile = profile
        user.onboarding_completed = True
        flag_modified(user, "onboarding_profile")
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        indexed, _ = self._replace_onboarding_vectors(user, profile)
        return indexed

    def _replace_onboarding_vectors(
        self, user: User, profile: Dict[str, Any]
    ) -> Tuple[int, Optional[str]]:
        user_data = {
            "db_user_id": user.id,
            "company": user.company,
            "user_id": user.phone,
        }
        tenant_id = resolve_effective_rag_tenant_id(user_data)
        text = format_onboarding_document(profile, company=user.company or "")
        client = ConversationVectorClient()
        if tenant_id and client.enabled():
            try:
                client.delete_points(tenant_id=tenant_id, sources=[ONBOARDING_SOURCE])
            except Exception as e:
                logger.warning(
                    "[ONBOARDING] Failed clearing previous onboarding vectors: %s",
                    e,
                    exc_info=True,
                )

        indexed, detail = index_extracted_text_for_user(
            user_data=user_data,
            object_key=ONBOARDING_OBJECT_KEY,
            file_name=ONBOARDING_FILE_NAME,
            extracted_text=text,
            source=ONBOARDING_SOURCE,
        )
        if detail:
            logger.warning(
                "[ONBOARDING] Index detail for user %s: chunks=%s detail=%s",
                user.id,
                indexed,
                detail,
            )
        else:
            logger.info(
                "[ONBOARDING] Indexed business profile for user %s chunks=%s",
                user.id,
                indexed,
            )
        return indexed, detail


def _answers_from_profile(profile: Dict[str, Any]) -> Dict[str, str]:
    raw = profile.get("answers") if isinstance(profile.get("answers"), dict) else profile
    if not isinstance(raw, dict):
        return {}
    out: Dict[str, str] = {}
    for key, value in raw.items():
        if key in {"completed_at", "updated_at", "version", "answers"}:
            continue
        text = _clean_answer(value)
        if text:
            out[str(key)] = text
    return out


def _clean_answer(value: Any) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text
