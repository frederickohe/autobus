"""Factory utility for creating agents with proper configuration."""

from typing import Dict, Any, List, Optional, Union
from smolagents import ToolCallingAgent, Tool


def create_agent_with_defaults(
    model: Union[Any, object],
    tools: List[Tool],
    name: str,
    description: str,
    prompt_templates: Optional[Dict[str, Any]] = None,
    max_steps: int = 6,
    **kwargs
) -> ToolCallingAgent:
    """Create a ToolCallingAgent with default authorized_imports.
    
    Args:
        model: The model to use (e.g., InferenceClientModel or OpenAIModelForSmolagents).
        tools: List of tools available to the agent.
        name: Name of the agent.
        description: Description of the agent.
        prompt_templates: Optional custom prompt templates dict.
        max_steps: Maximum steps for the agent.
        **kwargs: Additional arguments to pass to ToolCallingAgent.
        
    Returns:
        Configured ToolCallingAgent instance.
    """
    # Ensure prompt_templates includes authorized_imports
    if prompt_templates is None:
        prompt_templates = {}
    
    if not isinstance(prompt_templates, dict):
        # If prompt_templates is passed but not a dict, initialize it as a dict
        prompt_templates = {}
    
    if 'authorized_imports' not in prompt_templates:
        prompt_templates['authorized_imports'] = (
            "math, datetime, json, re, csv, os, sys, collections, itertools, "
            "functools, operator, statistics, requests, pandas, numpy, pathlib, typing, urllib"
        )
    
    return ToolCallingAgent(
        model=model,
        tools=tools,
        name=name,
        description=description,
        max_steps=max_steps,
        prompt_templates=prompt_templates,
        **kwargs
    )
