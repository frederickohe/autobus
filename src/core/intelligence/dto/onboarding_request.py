from typing import Dict

from pydantic import BaseModel, Field


class OnboardingSubmitRequest(BaseModel):
    answers: Dict[str, str] = Field(
        ...,
        description="Map of question id to the owner's answer. Select questions must use a catalog option.",
    )
