import os
import json
import hashlib
import logging
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from smolagents.tools import Tool
import redis
from pathlib import Path

logger = logging.getLogger(__name__)


class ImageGenerationTool(Tool):
    """Tool for generating images using OpenAI's DALL-E API"""
    
    name = "image_generation_tool"
    description = """Generate images from text descriptions using OpenAI's DALL-E model.
    Supports high-quality image generation with various sizes and styles."""
    
    inputs = {
        'prompt': {
            'type': 'string',
            'description': 'Text description of the image to generate',
            'required': True
        },
        'user_id': {
            'type': 'string',
            'description': 'User ID requesting the image generation',
            'required': True
        },
        'size': {
            'type': 'string',
            'description': 'Image size: 1024x1024, 1792x1024, or 1024x1792',
            'default': '1024x1024',
            'nullable': True
        },
        'quality': {
            'type': 'string',
            'description': 'Quality level: standard or hd',
            'default': 'standard',
            'nullable': True
        },
        'style': {
            'type': 'string',
            'description': 'Style preset: natural or vivid',
            'default': 'natural',
            'nullable': True
        },
        'num_images': {
            'type': 'integer',
            'description': 'Number of images to generate (1-4)',
            'default': 1,
            'nullable': True
        }
    }
    output_type = "string"

    def __init__(self, redis_client=None, storage_path=None):
        """
        Initialize ImageGenerationTool
        
        Args:
            redis_client: Redis client for caching and rate limiting
            storage_path: Path to store generated images locally
        """
        super().__init__()
        redis_password = os.getenv('REDIS_PASSWORD', 'autobus098')
        self.redis = redis_client or redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            password=redis_password if redis_password else None,
            db=0,
            decode_responses=True
        )
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.storage_path = storage_path or os.path.join(
            os.path.dirname(__file__), 'generated_images'
        )
        
        # Create storage directory if it doesn't exist
        Path(self.storage_path).mkdir(parents=True, exist_ok=True)
        
        # Configuration
        self.config = {
            'model': 'dall-e-3',  # Can be dall-e-3 or dall-e-2
            'rate_limit_per_user': 10,  # images per hour
            'rate_limit_per_day': 50,  # images per day
            'save_locally': True,
            'tracking_enabled': True,
            'valid_sizes': {
                'dall-e-3': ['1024x1024', '1792x1024', '1024x1792'],
                'dall-e-2': ['256x256', '512x512', '1024x1024']
            },
            'valid_qualities': ['standard', 'hd'],
            'valid_styles': ['natural', 'vivid']
        }

    def _check_rate_limit(self, user_id: str) -> Dict[str, Any]:
        """
        Check if user has exceeded rate limits
        
        Args:
            user_id: User requesting image generation
            
        Returns:
            Dict with 'allowed' (bool) and 'reason' (str)
        """
        current_hour = datetime.now().strftime('%Y%m%d%H')
        current_day = datetime.now().strftime('%Y%m%d')
        
        # Check hourly limit
        hourly_key = f"rate:image:{user_id}:hour:{current_hour}"
        hourly_count = int(self.redis.get(hourly_key) or 0)
        
        if hourly_count >= self.config['rate_limit_per_user']:
            return {
                'allowed': False,
                'reason': f"Hourly limit exceeded ({hourly_count}/{self.config['rate_limit_per_user']})"
            }
        
        # Check daily limit
        daily_key = f"rate:image:{user_id}:day:{current_day}"
        daily_count = int(self.redis.get(daily_key) or 0)
        
        if daily_count >= self.config['rate_limit_per_day']:
            return {
                'allowed': False,
                'reason': f"Daily limit exceeded ({daily_count}/{self.config['rate_limit_per_day']})"
            }
        
        return {'allowed': True, 'reason': None}

    def _validate_parameters(self, size: str, quality: str, style: str, num_images: int) -> Optional[str]:
        """Validate input parameters"""
        model = self.config['model']
        valid_sizes = self.config['valid_sizes'].get(model, [])
        
        if size not in valid_sizes:
            return f"Invalid size '{size}'. Valid sizes: {', '.join(valid_sizes)}"
        
        if quality not in self.config['valid_qualities']:
            return f"Invalid quality '{quality}'. Valid qualities: {', '.join(self.config['valid_qualities'])}"
        
        if style not in self.config['valid_styles']:
            return f"Invalid style '{style}'. Valid styles: {', '.join(self.config['valid_styles'])}"
        
        if not (1 <= num_images <= 4):
            return "Number of images must be between 1 and 4"
        
        if len(size.encode()) > 2000:
            return "Prompt is too long (max 2000 characters)"
        
        return None

    def _update_rate_limit(self, user_id: str, count: int = 1):
        """Update rate limit counters"""
        current_hour = datetime.now().strftime('%Y%m%d%H')
        current_day = datetime.now().strftime('%Y%m%d')
        
        hourly_key = f"rate:image:{user_id}:hour:{current_hour}"
        daily_key = f"rate:image:{user_id}:day:{current_day}"
        
        # Increment hourly counter (expires after 1 hour)
        self.redis.incrby(hourly_key, count)
        self.redis.expire(hourly_key, 3600)
        
        # Increment daily counter (expires after 24 hours)
        self.redis.incrby(daily_key, count)
        self.redis.expire(daily_key, 86400)

    def _track_image_generation(self, user_id: str, prompt: str, image_urls: List[str], 
                               size: str, quality: str, style: str) -> str:
        """Track generated images for analytics and retrieval"""
        tracking_id = hashlib.md5(
            f"{user_id}:{prompt}:{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]
        
        tracking_data = {
            'tracking_id': tracking_id,
            'user_id': user_id,
            'prompt': prompt,
            'image_urls': image_urls,
            'size': size,
            'quality': quality,
            'style': style,
            'timestamp': datetime.now().isoformat(),
            'model': self.config['model'],
            'num_images': len(image_urls)
        }
        
        # Store in Redis for quick retrieval (7 days expiration)
        self.redis.setex(
            f"image:track:{tracking_id}",
            86400 * 7,
            json.dumps(tracking_data)
        )
        
        logger.info(f"Image generation tracked: {tracking_id}")
        return tracking_id

    def _save_image_locally(self, user_id: str, image_url: str, tracking_id: str, index: int) -> Optional[str]:
        """
        Download and save image locally
        
        Args:
            user_id: User ID
            image_url: URL of the generated image
            tracking_id: Tracking ID for the generation request
            index: Image index (0-based)
            
        Returns:
            Local file path or None if save fails
        """
        try:
            # Download image
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            
            # Create user-specific directory
            user_dir = os.path.join(self.storage_path, user_id)
            Path(user_dir).mkdir(parents=True, exist_ok=True)
            
            # Save with tracking ID
            filename = f"{tracking_id}_{index}.png"
            filepath = os.path.join(user_dir, filename)
            
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"Image saved locally: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error saving image locally: {e}")
            return None

    def _generate_with_openai(self, prompt: str, size: str, quality: str, style: str, 
                             num_images: int) -> Optional[List[str]]:
        """
        Call OpenAI DALL-E API to generate images
        
        Args:
            prompt: Text description
            size: Image size
            quality: Quality level
            style: Style preset
            num_images: Number of images to generate
            
        Returns:
            List of image URLs or None if generation fails
        """
        try:
            from openai import OpenAI
            
            client = OpenAI(api_key=self.openai_api_key)
            
            logger.info(f"Generating {num_images} image(s) with DALL-E")
            logger.debug(f"Prompt: {prompt[:100]}...")
            
            response = client.images.generate(
                model=self.config['model'],
                prompt=prompt,
                size=size,
                quality=quality,
                style=style,
                n=num_images
            )
            
            image_urls = [img.url for img in response.data]
            logger.info(f"Successfully generated {len(image_urls)} image(s)")
            
            return image_urls
            
        except Exception as e:
            logger.error(f"Error generating images with OpenAI: {e}")
            return None

    def forward(self, prompt: str, user_id: str, size: str = '1024x1024', 
               quality: str = 'standard', style: str = 'natural', num_images: int = 1) -> str:
        """
        Generate images from text prompt
        
        Args:
            prompt: Text description of desired image
            user_id: User requesting image generation
            size: Image size (1024x1024, 1792x1024, 1024x1792)
            quality: Quality level (standard or hd)
            style: Style (natural or vivid)
            num_images: Number of images to generate (1-4)
            
        Returns:
            Response string with image URLs and tracking information
        """
        try:
            # Validate parameters
            validation_error = self._validate_parameters(size, quality, style, num_images)
            if validation_error:
                return f"❌ {validation_error}"
            
            # Check rate limiting
            rate_check = self._check_rate_limit(user_id)
            if not rate_check['allowed']:
                return f"❌ Rate limit exceeded: {rate_check['reason']}"
            
            # Validate prompt
            if not prompt or len(prompt.strip()) == 0:
                return "❌ Prompt cannot be empty"
            
            if len(prompt) > 4000:
                return "❌ Prompt too long (max 4000 characters)"
            
            # Generate images
            image_urls = self._generate_with_openai(prompt, size, quality, style, num_images)
            if not image_urls:
                return "❌ Failed to generate images. Please try again or check your prompt."
            
            # Track generation
            tracking_id = self._track_image_generation(
                user_id, prompt, image_urls, size, quality, style
            )
            
            # Update rate limits
            self._update_rate_limit(user_id, num_images)
            
            # Save locally if enabled
            local_paths = []
            if self.config['save_locally']:
                for idx, url in enumerate(image_urls):
                    local_path = self._save_image_locally(user_id, url, tracking_id, idx)
                    if local_path:
                        local_paths.append(local_path)
            
            # Build response
            response = f"✅ Successfully generated {len(image_urls)} image(s)\n\n"
            response += f"📋 Prompt: {prompt}\n"
            response += f"🎨 Settings: {size} • {quality} • {style}\n"
            response += f"🆔 Tracking ID: {tracking_id}\n\n"
            response += f"🖼️ Generated Images:\n"
            
            for idx, url in enumerate(image_urls, 1):
                response += f"\n**Image {idx}:**\n"
                response += f"  URL: {url}\n"
                if idx - 1 < len(local_paths):
                    response += f"  Local: {local_paths[idx - 1]}\n"
            
            return response
            
        except Exception as e:
            logger.error(f"Error in image generation: {e}", exc_info=True)
            return f"❌ Error generating images: {str(e)}"

    def get_generation_history(self, user_id: str, limit: int = 10) -> Dict[str, Any]:
        """
        Retrieve image generation history for a user
        
        Args:
            user_id: User ID
            limit: Maximum number of records to return
            
        Returns:
            Dictionary with generation history
        """
        try:
            pattern = f"image:track:*"
            keys = self.redis.keys(pattern)
            
            generations = []
            for key in keys:
                data = self.redis.get(key)
                if data:
                    track_data = json.loads(data)
                    if track_data.get('user_id') == user_id:
                        generations.append(track_data)
            
            # Sort by timestamp (newest first)
            generations.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            return {
                'user_id': user_id,
                'total': len(generations),
                'generations': generations[:limit]
            }
        except Exception as e:
            logger.error(f"Error retrieving generation history: {e}")
            return {'user_id': user_id, 'total': 0, 'generations': []}

    def delete_image(self, tracking_id: str, image_index: int = 0) -> bool:
        """Delete a generated image"""
        try:
            tracking_data = self.redis.get(f"image:track:{tracking_id}")
            if not tracking_data:
                return False
            
            data = json.loads(tracking_data)
            user_id = data.get('user_id')
            
            # Delete local file
            filename = f"{tracking_id}_{image_index}.png"
            filepath = os.path.join(self.storage_path, user_id, filename)
            
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"Deleted image: {filepath}")
            
            return True
        except Exception as e:
            logger.error(f"Error deleting image: {e}")
            return False
