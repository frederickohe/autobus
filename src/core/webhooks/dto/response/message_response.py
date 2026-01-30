from pydantic import BaseModel


class AubobusResponse(BaseModel):
    message: str