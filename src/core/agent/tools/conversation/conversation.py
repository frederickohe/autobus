from smolagents.tools import Tool
from huggingface_hub import InferenceClient
import os

class ConversationTool(Tool):
    name = "assistant_conversation"
    description = (
        "Generates a conversational response to a user message. "
        "Use this for greetings, small talk, and general conversation."
    )
    inputs = {
        "message": {
            "type": "string",
            "description": "The user's message to respond to."
        }
    }
    output_type = "string"

    def __init__(
        self,
        model_id: str = "meta-llama/Llama-3.2-3B-Instruct",
        max_tokens: int = 256,
        temperature: float = 0.7
    ):
        super().__init__()
        # Use the Hugging Face Inference API – make sure your token is set in the environment
        self.client = InferenceClient(model=model_id)
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.conversation_history = []  # stores messages with roles

    def forward(self, message: str) -> str:
        # Prevent processing the same assistant response as a new user message
        if self.conversation_history:
            last = self.conversation_history[-1]
            if last.get("role") == "assistant" and message.strip() == last.get("content", "").strip():
                # This looks like the agent feeding the previous assistant output back into the tool.
                # Ignore and return the message unchanged to avoid a self-loop.
                return message

        # Add user message to history
        self.conversation_history.append({"role": "user", "content": message})

        # Keep history bounded to avoid runaway loops and token bloat
        max_history = 20
        if len(self.conversation_history) > max_history * 2:
            # trim to last `max_history` pairs
            self.conversation_history = self.conversation_history[-(max_history * 2):]

        # Prepare the full conversation for the model
        messages = self.conversation_history.copy()

        try:
            response = self.client.chat.completions.create(
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                stream=False
            )
            assistant_message = response.choices[0].message.content
            # Add assistant response to history
            self.conversation_history.append({"role": "assistant", "content": assistant_message})
            return assistant_message
        except Exception as e:
            error_msg = f"❌ Error generating conversation: {str(e)}"
            return error_msg

    def reset_conversation(self):
        """Clear the conversation history (useful for starting a fresh chat)."""
        self.conversation_history = []