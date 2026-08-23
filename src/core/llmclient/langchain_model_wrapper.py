"""LangChain Model Wrapper for AutoBus

This module provides a LangChain-compatible wrapper around the OpenRouter
OpenAI-compatible API, integrating with the existing LLMClient while supporting
LangChain's agent and tool framework.
"""

import logging
from typing import Dict, List, Any, Optional
from langchain_openai import ChatOpenAI
from langchain.schema import BaseMessage, HumanMessage, SystemMessage, AIMessage
import os
from dotenv import load_dotenv
from core.nlu.config import (
    LLM_API_KEY,
    LLM_APP_TITLE,
    LLM_BASE_URL,
    LLM_HTTP_REFERER,
    MODEL,
)

logger = logging.getLogger(__name__)

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env')
load_dotenv(env_path)


class LangChainOpenAIWrapper:
    """
    LangChain-compatible wrapper for OpenRouter-hosted chat models.
    """

    def __init__(
        self,
        model_name: str = MODEL,
        temperature: float = 0.5,
        max_tokens: int = 2096,
        api_key: Optional[str] = None
    ):
        """
        Args:
            model_name: OpenRouter model slug (e.g. openai/gpt-oss-120b)
            temperature: Creativity level (0-1), default 0.5
            max_tokens: Maximum tokens for responses, default 2096
            api_key: API key (defaults to OPENROUTER_API_KEY / LLM_API_KEY)
        """
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens

        self.api_key = api_key or LLM_API_KEY or os.getenv("OPENROUTER_API_KEY")

        headers = {}
        if LLM_HTTP_REFERER:
            headers["HTTP-Referer"] = LLM_HTTP_REFERER
        if LLM_APP_TITLE:
            headers["X-OpenRouter-Title"] = LLM_APP_TITLE

        self.llm = ChatOpenAI(
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=self.api_key,
            base_url=LLM_BASE_URL,
            default_headers=headers or None,
            request_timeout=120
        )

        logger.info("Initialized LangChain LLM wrapper with model: %s", model_name)
    
    def __call__(self, prompt: str, **kwargs) -> str:
        """
        Process a prompt using the configured chat model.
        
        Args:
            prompt: The input prompt/message
            **kwargs: Additional arguments (temperature, max_tokens, etc.)
            
        Returns:
            Model's response as string
        """
        return self.invoke(prompt, **kwargs)
    
    def invoke(self, prompt: str, **kwargs) -> str:
        """
        Invoke the model with a text prompt.
        
        Args:
            prompt: The input prompt
            **kwargs: Additional arguments
            
        Returns:
            Model's response as string
        """
        try:
            # Create a message
            messages = [HumanMessage(content=prompt)]
            
            # Get response
            response = self.llm(messages)
            
            # Return the content as string
            return response.content
        except Exception as e:
            logger.error(f"Error invoking LLM: {e}", exc_info=True)
            raise
    
    def invoke_with_messages(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Process messages in chat format.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            system_prompt: Optional system prompt
            **kwargs: Additional arguments
            
        Returns:
            Model's response as string
        """
        try:
            # Build message list
            langchain_messages = []
            
            # Add system prompt if provided
            if system_prompt:
                langchain_messages.append(SystemMessage(content=system_prompt))
            
            # Add conversation messages
            for msg in messages:
                role = msg.get("role", "user").lower()
                content = msg.get("content", "")
                
                if role == "system":
                    langchain_messages.append(SystemMessage(content=content))
                elif role == "assistant":
                    langchain_messages.append(AIMessage(content=content))
                else:  # user or default
                    langchain_messages.append(HumanMessage(content=content))
            
            # Get response
            response = self.llm(langchain_messages)
            
            # Return content as string
            return response.content
        except Exception as e:
            logger.error(f"Error invoking LLM with messages: {e}", exc_info=True)
            raise
    
    def get_langchain_llm(self):
        """
        Get the underlying LangChain ChatOpenAI instance.
        
        Returns:
            ChatOpenAI instance for use with LangChain agents and tools
        """
        return self.llm
