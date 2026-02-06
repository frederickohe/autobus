from pydantic import BaseModel


class AutobusResponse(BaseModel):
    message: str