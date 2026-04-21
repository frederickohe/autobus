"""LangChain Tool Base Class

Provides a wrapper to easily migrate from Smolagents Tools to LangChain Tools
while maintaining backward compatibility with existing tool implementations.
"""

import logging
from typing import Any, Dict, Optional, Callable
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from langchain.tools import BaseTool

logger = logging.getLogger(__name__)


class LangChainToolWrapper(BaseTool):
    """
    Base class for LangChain-compatible tools.
    
    This class wraps the pattern used in smolagents tools to work seamlessly with LangChain.
    Subclasses should define:
    - name: Tool name
    - description: Tool description
    - input_schema: Pydantic model for tool inputs
    - _run(): Implementation of the tool
    """
    
    # These should be overridden in subclasses
    name: str = "base_tool"
    description: str = "Base tool"
    
    def _run(self, **kwargs) -> str:
        """
        Execute the tool.
        
        Args:
            **kwargs: Tool-specific arguments as defined in input_schema
            
        Returns:
            String result of the tool execution
        """
        raise NotImplementedError("Subclasses must implement _run()")
    
    async def _arun(self, **kwargs) -> str:
        """
        Async version of _run. Defaults to calling _run in an executor.
        
        Args:
            **kwargs: Tool-specific arguments as defined in input_schema
            
        Returns:
            String result of the tool execution
        """
        return self._run(**kwargs)


class ToolInput(BaseModel):
    """Base input schema - override this in subclasses"""
    pass


def create_langchain_tool(
    name: str,
    description: str,
    func: Callable,
    input_schema: Optional[BaseModel] = None,
    **kwargs
) -> BaseTool:
    """
    Create a LangChain tool from a simple function.
    
    This is useful for converting simple functions or tools that don't need complex input validation.
    
    Args:
        name: Name of the tool
        description: Description of what the tool does
        func: Function to execute when tool is called
        input_schema: Optional Pydantic BaseModel for input validation
        **kwargs: Additional arguments to pass to tool creation
        
    Returns:
        LangChain Tool instance
    """
    from langchain.tools import tool
    
    # Create the tool with @tool decorator pattern
    @tool(name=name, description=description)
    def wrapper(**input_kwargs) -> str:
        """Wrapper for the tool function"""
        return str(func(**input_kwargs))
    
    return wrapper


class ConvertSmolagentsToolToLangChain(BaseTool):
    """
    Adapter to convert existing Smolagents-style tools to LangChain tools.
    
    This allows gradual migration by wrapping old-style tools without changing their implementation.
    
    Example:
        old_tool = MyOldSmolagentsTool()
        new_tool = ConvertSmolagentsToolToLangChain.from_smolagents_tool(old_tool)
    """
    
    _smolagents_tool: Any = None
    name: str = "converted_tool"
    description: str = "Converted from smolagents tool"
    
    def __init__(self, smolagents_tool: Any, **kwargs):
        """
        Initialize the adapter.
        
        Args:
            smolagents_tool: The smolagents Tool instance to wrap
            **kwargs: Additional arguments
        """
        # Extract name and description from smolagents tool
        tool_name = getattr(smolagents_tool, 'name', 'tool')
        tool_description = getattr(smolagents_tool, 'description', 'A tool')
        
        super().__init__(name=tool_name, description=tool_description)
        self._smolagents_tool = smolagents_tool
    
    def _run(self, **kwargs) -> str:
        """
        Execute the wrapped smolagents tool.
        
        Args:
            **kwargs: Arguments to pass to the tool's forward() method
            
        Returns:
            String result from the tool
        """
        try:
            # Call the forward method of the smolagents tool
            result = self._smolagents_tool.forward(**kwargs)
            return str(result)
        except Exception as e:
            logger.error(f"Error executing smolagents tool {self.name}: {e}")
            return f"Error: {str(e)}"
    
    async def _arun(self, **kwargs) -> str:
        """Async version - delegates to _run"""
        return self._run(**kwargs)
    
    @classmethod
    def from_smolagents_tool(cls, smolagents_tool: Any) -> 'ConvertSmolagentsToolToLangChain':
        """
        Create a LangChain tool from a Smolagents tool.
        
        Args:
            smolagents_tool: Smolagents Tool instance
            
        Returns:
            LangChain-compatible tool
        """
        return cls(smolagents_tool)


def migrate_smolagents_tool_inputs_to_langchain(
    smolagents_inputs: Dict[str, Dict[str, Any]]
) -> BaseModel:
    """
    Convert smolagents-style input schema to LangChain Pydantic BaseModel.
    
    Smolagents uses a dict-based schema:
    ```
    inputs = {
        'param1': {
            'type': 'string',
            'description': '...',
            'required': True,
        }
    }
    ```
    
    This converts it to a LangChain Pydantic model.
    
    Args:
        smolagents_inputs: The inputs dict from a smolagents tool
        
    Returns:
        Pydantic BaseModel class
    """
    fields = {}
    
    for param_name, param_config in smolagents_inputs.items():
        param_type = param_config.get('type', 'string')
        is_required = param_config.get('required', False)
        description = param_config.get('description', '')
        default_value = param_config.get('default')
        
        # Map smolagents types to Python types
        type_mapping = {
            'string': str,
            'integer': int,
            'float': float,
            'boolean': bool,
            'object': dict,
            'array': list,
        }
        
        python_type = type_mapping.get(param_type, str)
        
        # Create field
        if is_required and default_value is None:
            field = Field(..., description=description)
        else:
            field = Field(default=default_value, description=description)
        
        fields[param_name] = (python_type, field)
    
    # Create and return the Pydantic model
    return type('ToolInput', (BaseModel,), {'__annotations__': {k: v[0] for k, v in fields.items()}, **{k: v[1] for k, v in fields.items()}})
