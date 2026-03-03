"""Image storage utility for handling agent-generated images."""
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
from smolagents.agent_types import AgentImage, AgentAudio

logger = logging.getLogger(__name__)


class ImageStorageManager:
    """Manages storage of agent-generated images and audio files."""
    
    def __init__(self, base_dir: str = "agent_outputs"):
        """Initialize image storage manager.
        
        Args:
            base_dir: Base directory for storing images and audio files.
        """
        self.base_dir = base_dir
        self.images_dir = os.path.join(base_dir, "images")
        self.audio_dir = os.path.join(base_dir, "audio")
        
        # Create directories if they don't exist
        os.makedirs(self.images_dir, exist_ok=True)
        os.makedirs(self.audio_dir, exist_ok=True)
    
    def save_agent_image(self, agent_image: AgentImage, user_id: str) -> Tuple[str, str]:
        """Save an AgentImage to disk and return the file path and reference string.
        
        Args:
            agent_image: The AgentImage object from the agent response.
            user_id: The user ID to organize files by.
            
        Returns:
            Tuple of (file_path, reference_string) where reference_string is suitable
            for storing in conversation history.
        """
        try:
            # Get the image path from the AgentImage object
            image_path = agent_image.to_string()
            
            if not os.path.exists(image_path):
                logger.warning(f"Agent image path does not exist: {image_path}")
                return None, f"[Image generation failed - file not found]"
            
            # Create user-specific subdirectory
            user_image_dir = os.path.join(self.images_dir, user_id)
            os.makedirs(user_image_dir, exist_ok=True)
            
            # Generate unique filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"agent_image_{timestamp}.png"
            destination_path = os.path.join(user_image_dir, filename)
            
            # Copy the file
            import shutil
            shutil.copy2(image_path, destination_path)
            
            logger.info(f"Saved agent image for user {user_id} to {destination_path}")
            
            # Return both the file path and a reference string for conversation history
            reference_string = f"[Image generated and saved: {destination_path}]"
            return destination_path, reference_string
            
        except Exception as e:
            logger.error(f"Error saving agent image: {str(e)}", exc_info=True)
            return None, f"[Image generation failed: {str(e)}]"
    
    def save_agent_audio(self, agent_audio: AgentAudio, user_id: str) -> Tuple[str, str]:
        """Save an AgentAudio to disk and return the file path and reference string.
        
        Args:
            agent_audio: The AgentAudio object from the agent response.
            user_id: The user ID to organize files by.
            
        Returns:
            Tuple of (file_path, reference_string) where reference_string is suitable
            for storing in conversation history.
        """
        try:
            # Get the audio path from the AgentAudio object
            audio_path = agent_audio.to_string()
            
            if not os.path.exists(audio_path):
                logger.warning(f"Agent audio path does not exist: {audio_path}")
                return None, f"[Audio generation failed - file not found]"
            
            # Create user-specific subdirectory
            user_audio_dir = os.path.join(self.audio_dir, user_id)
            os.makedirs(user_audio_dir, exist_ok=True)
            
            # Generate unique filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"agent_audio_{timestamp}.wav"
            destination_path = os.path.join(user_audio_dir, filename)
            
            # Copy the file
            import shutil
            shutil.copy2(audio_path, destination_path)
            
            logger.info(f"Saved agent audio for user {user_id} to {destination_path}")
            
            # Return both the file path and a reference string for conversation history
            reference_string = f"[Audio generated and saved: {destination_path}]"
            return destination_path, reference_string
            
        except Exception as e:
            logger.error(f"Error saving agent audio: {str(e)}", exc_info=True)
            return None, f"[Audio generation failed: {str(e)}]"
    
    @staticmethod
    def is_media_response(response) -> bool:
        """Check if response is a media object (image or audio).
        
        Args:
            response: The response object to check.
            
        Returns:
            True if response is AgentImage or AgentAudio, False otherwise.
        """
        return isinstance(response, (AgentImage, AgentAudio))
    
    def handle_media_response(self, response, user_id: str) -> Tuple[Optional[str], str]:
        """Handle media responses by saving them and returning appropriate strings.
        
        Args:
            response: The response object that may contain media.
            user_id: The user ID to organize files by.
            
        Returns:
            Tuple of (file_path, conversation_string) where conversation_string
            is suitable for storing in conversation history.
        """
        if isinstance(response, AgentImage):
            return self.save_agent_image(response, user_id)
        elif isinstance(response, AgentAudio):
            return self.save_agent_audio(response, user_id)
        else:
            # Not a media response, return as-is
            return None, str(response)
