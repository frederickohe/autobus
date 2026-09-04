from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class AgentAttachment(BaseModel):
    kind: str = Field(..., min_length=1, max_length=32)
    url: Optional[str] = Field(None, max_length=2048)
    name: Optional[str] = Field(None, max_length=255)
    mime: Optional[str] = Field(None, max_length=128)


class AgentTurnRequest(BaseModel):
    message: Optional[str] = Field(None, max_length=8000)
    attachments: List[AgentAttachment] = Field(default_factory=list)
    confirm_id: Optional[str] = Field(None, max_length=64)
    confirmed: Optional[bool] = None
    ask_id: Optional[str] = Field(None, max_length=64)

    @model_validator(mode="after")
    def require_payload(self):
        text = (self.message or "").strip()
        if text or self.attachments or self.confirm_id or self.ask_id:
            return self
        raise ValueError("Provide a message, attachment, or a response to a prompt")


class AgentAskChoice(BaseModel):
    id: str
    label: str


class AgentAskSpec(BaseModel):
    id: str
    kind: str
    prompt: str
    accept: List[str] = Field(default_factory=list)
    choices: List[AgentAskChoice] = Field(default_factory=list)


class AgentConfirmSpec(BaseModel):
    id: str
    title: str
    summary: str
    tool: str
    payload: Dict[str, Any] = Field(default_factory=dict)


class AgentActionLog(BaseModel):
    tool: str
    ok: bool = True
    detail: str = ""


class AgentTurnResponse(BaseModel):
    message: str
    success: bool = True
    used_llm: bool = False
    turn_type: str = "reply"
    ask: Optional[AgentAskSpec] = None
    confirm: Optional[AgentConfirmSpec] = None
    actions: List[AgentActionLog] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)
