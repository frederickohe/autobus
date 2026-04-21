from typing import Any, Optional
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
import json


class FinalAnswerInput(BaseModel):
    """Input schema for FinalAnswerTool"""
    answer: Any = Field(..., description="The final answer to the problem")


class FinalAnswerTool(BaseTool):
    """LangChain tool for providing a final answer."""
    
    name: str = "final_answer"
    description: str = "Provides a final answer to the given problem."
    args_schema: type[BaseModel] = FinalAnswerInput

    def _run(self, answer: Any) -> str:
        """Execute the tool to provide a final answer.
        
        Args:
            answer: The answer to return
            
        Returns:
            String representation of the answer
        """
        if isinstance(answer, str):
            return answer
        return json.dumps(answer) if isinstance(answer, (dict, list)) else str(answer)

    async def _arun(self, answer: Any) -> str:
        """Async version of _run.
        
        Args:
            answer: The answer to return
            
        Returns:
            String representation of the answer
        """
        return self._run(answer)
