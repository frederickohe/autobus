from pydantic import BaseModel, Field, validator
from typing import Optional, List
import json


class UpdatePlanRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Name of the subscription plan")
    price: Optional[float] = Field(None, gt=0, description="Monthly price of the plan")
    features: Optional[List[str]] = Field(None, description="List of features")
    agents: Optional[List[str]] = Field(None, description="List of agent identifiers to provision for this plan")
    description: Optional[str] = Field(None, max_length=500, description="Description of the plan")
    is_active: Optional[bool] = Field(None, description="Whether the plan is active")
    
    @validator('features', pre=True)
    def convert_features_to_string(cls, v):
        if v is None:
            return None
        if isinstance(v, list):
            return json.dumps(v)
        if isinstance(v, str):
            # Try to parse to ensure it's valid JSON
            try:
                json.loads(v)
                return v
            except (json.JSONDecodeError, TypeError):
                # If it's a plain string, convert it to JSON list
                return json.dumps([v])
        return v

    @validator('agents', pre=True)
    def convert_agents_to_string(cls, v):
        if v is None:
            return None
        if isinstance(v, list):
            return json.dumps(v)
        if isinstance(v, str):
            try:
                json.loads(v)
                return v
            except (json.JSONDecodeError, TypeError):
                return json.dumps([v])
        return v