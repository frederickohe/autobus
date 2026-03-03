from pydantic import BaseModel

class CommandRequest(BaseModel):
    userid: str
    message: str
    agent_name: str
