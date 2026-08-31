from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, field_validator


_FIELD_MAX = {
    "fullname": 255,
    "email": 255,
    "phone": 40,
    "profile_picture_url": 200,
    "nationality": 100,
    "gender": 50,
    "address": 300,
    "location": 255,
    "ghana_card": 100,
    "company": 255,
    "current_branch": 100,
    "staff_id": 50,
    "facebook_url": 200,
    "whatsapp_number": 20,
    "linkedin_url": 200,
    "twitter_url": 200,
    "instagram_url": 200,
}

_GENDER_ALIASES = {
    "m": "Male",
    "male": "Male",
    "f": "Female",
    "female": "Female",
    "other": "Other",
    "prefer not to say": "Prefer not to say",
    "prefer_not_to_say": "Prefer not to say",
    "unspecified": "Prefer not to say",
}


def _blank_to_none(value):
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None
    return value


class UserUpdateRequest(BaseModel):
    fullname: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    profile_picture_url: Optional[str] = None

    nationality: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    location: Optional[str] = None
    ghana_card: Optional[str] = None

    company: Optional[str] = None
    current_branch: Optional[str] = None
    staff_id: Optional[str] = None

    facebook_url: Optional[str] = None
    whatsapp_number: Optional[str] = None
    linkedin_url: Optional[str] = None
    twitter_url: Optional[str] = None
    instagram_url: Optional[str] = None

    profile_sharing: Optional[bool] = None
    in_app_notification: Optional[bool] = None
    sms_notification: Optional[bool] = None
    currency_code: Optional[str] = None

    @field_validator("date_of_birth", mode="before")
    @classmethod
    def parse_date_of_birth(cls, value):
        if value in (None, ""):
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        text = str(value).strip()
        if not text:
            return None
        if "T" in text:
            text = text.split("T", 1)[0]
        try:
            return date.fromisoformat(text[:10])
        except ValueError as exc:
            raise ValueError("Date of birth must be YYYY-MM-DD") from exc

    @field_validator("currency_code", mode="before")
    @classmethod
    def normalize_currency_code(cls, value):
        text = _blank_to_none(value)
        if text is None:
            return None
        from core.user.currency import SUPPORTED_CURRENCIES, normalize_currency_code

        code = normalize_currency_code(text)
        allowed = {item[0] for item in SUPPORTED_CURRENCIES}
        if str(text).strip().upper() not in allowed:
            raise ValueError(f"Currency must be one of: {', '.join(sorted(allowed))}")
        return code

    @field_validator("gender", mode="before")
    @classmethod
    def normalize_gender(cls, value):
        text = _blank_to_none(value)
        if text is None:
            return None
        return _GENDER_ALIASES.get(text.lower(), text)

    @field_validator(
        "fullname",
        "email",
        "phone",
        "profile_picture_url",
        "nationality",
        "address",
        "location",
        "ghana_card",
        "company",
        "current_branch",
        "staff_id",
        "facebook_url",
        "whatsapp_number",
        "linkedin_url",
        "twitter_url",
        "instagram_url",
        mode="before",
    )
    @classmethod
    def clean_optional_text(cls, value, info):
        text = _blank_to_none(value)
        if text is None:
            return None
        limit = _FIELD_MAX.get(info.field_name)
        if limit and len(text) > limit:
            return text[:limit].rstrip()
        return text
