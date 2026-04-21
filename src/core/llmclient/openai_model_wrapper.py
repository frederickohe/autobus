"""OpenAI Model Wrapper for Smolagents Integration

This module provides a wrapper around the LLMClient to make it compatible with smolagents' model interface.
It allows smolagents to use OpenAI's ChatGPT API instead of the default HuggingFace Inference API.
"""

import logging
from typing import Dict, List, Any, Optional, Union
from core.llmclient.llmclient import LLMClient

try:
    from smolagents.models import ChatMessage
except ImportError:
    # Fallback if ChatMessage is not available
    ChatMessage = None

logger = logging.getLogger(__name__)


class OpenAIModelForSmolagents:
    """
    Wrapper to integrate OpenAI LLMClient with smolagents framework.
    
    This class adapts the LLMClient to the interface expected by smolagents,
    allowing tools and agents to use OpenAI's API for model interactions.
    """
    
    def __init__(
        self,
        model_name: str = "gpt-4o",
        max_tokens: int = 2096,
        temperature: float = 0.5
    ):
        """
        Initialize the OpenAI model wrapper for smolagents.
        
        Args:
            model_name: OpenAI model name (default: "gpt-4o" for multimodal)
            max_tokens: Maximum tokens for responses
            temperature: Creativity level (0-1)
        """
        self.llm_client = LLMClient()
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.temperature = temperature
        
        logger.info(f"Initialized OpenAI Model Wrapper for smolagents using {model_name}")
    
    def __call__(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """
        Process a prompt using OpenAI.
        
        Args:
            prompt: The input prompt/message
            stop: Stop sequences (not used with OpenAI in this implementation)
            **kwargs: Additional arguments (temperature, max_tokens, etc.)
            
        Returns:
            Model's response as string
        """
        temperature = kwargs.get('temperature', self.temperature)
        max_tokens = kwargs.get('max_tokens', self.max_tokens)
        
        logger.debug(f"Processing prompt with OpenAI (temp={temperature}, tokens={max_tokens})")
        
        response = self.llm_client.chat_completion(
            system_prompt="You are a helpful AI assistant.",
            user_message=prompt,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return response
    
    def forward(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """
        Alternative method name that some frameworks might use.
        Delegates to __call__.
        """
        return self.__call__(prompt, stop, **kwargs)
    
    def get_generated_text(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Explicit method for generating text with OpenAI.
        
        Args:
            prompt: The input prompt
            temperature: Override temperature
            max_tokens: Override max_tokens
            
        Returns:
            Generated text response
        """
        temp = temperature if temperature is not None else self.temperature
        tokens = max_tokens if max_tokens is not None else self.max_tokens
        
        return self.llm_client.chat_completion(
            system_prompt="You are a helpful AI assistant.",
            user_message=prompt,
            temperature=temp,
            max_tokens=tokens
        )
    
    def forward_with_messages(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Process messages in chat format.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            system_prompt: Optional system prompt override
            temperature: Override temperature
            max_tokens: Override max_tokens
            
        Returns:
            Model's response
        """
        # Format messages as conversation history
        conversation_history = [
            {"role": msg.get("role", "user"), "content": msg.get("content", "")}
            for msg in messages[:-1]  # All but last message
        ]
        
        # Last message is the current user message
        user_message = messages[-1]["content"] if messages else ""
        sys_prompt = system_prompt or "You are a helpful AI assistant."
        
        temp = temperature if temperature is not None else self.temperature
        tokens = max_tokens if max_tokens is not None else self.max_tokens
        
        return self.llm_client.chat_completion(
            system_prompt=sys_prompt,
            user_message=user_message,
            conversation_history=conversation_history,
            temperature=temp,
            max_tokens=tokens
        )
    
    def generate(
        self,
        messages: List[Dict[str, str]],
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """
        Generate a response using OpenAI based on message history.
        
        This is the primary method used by smolagents framework.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys.
                     Expected format: [{"role": "system"/"user"/"assistant", "content": "..."}, ...]
            stop: Stop sequences (optional, not used with OpenAI)
            **kwargs: Additional arguments like temperature, max_tokens, etc.
            
        Returns:
            Model's response as string
        """
        temperature = kwargs.get('temperature', self.temperature)
        max_tokens = kwargs.get('max_tokens', self.max_tokens)
        
        # Extract system prompt from messages
        system_prompt = "You are a helpful AI assistant."
        conversation_history = []
        user_message = ""
        
        if messages:
            # Look for system message first
            for msg in messages:
                if msg.get("role") == "system":
                    system_prompt = msg.get("content", system_prompt)
                    break
            
            # Extract conversation history (all non-system messages except the last)
            non_system_messages = [m for m in messages if m.get("role") != "system"]
            
            if len(non_system_messages) > 1:
                # All but the last message form conversation history
                conversation_history = non_system_messages[:-1]
            
            # Last non-system message is the current user message
            if non_system_messages:
                user_message = non_system_messages[-1].get("content", "")
        
        logger.debug(f"Generating with OpenAI (temp={temperature}, tokens={max_tokens})")
        logger.debug(f"Messages received: {len(messages)} total, system_prompt set: {system_prompt != 'You are a helpful AI assistant.'}")
        
        response = self.llm_client.chat_completion(
            system_prompt=system_prompt,
            user_message=user_message,
            conversation_history=conversation_history if conversation_history else None,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return response
