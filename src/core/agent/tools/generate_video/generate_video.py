import os
import json
import hashlib
import logging
import requests
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from smolagents.tools import Tool
import redis
from pathlib import Path

logger = logging.getLogger(__name__)


class VideoGenerationTool(Tool):
    """Tool for generating videos using Runway ML API"""
    
    name = "video_generation_tool"
    description = """Generate videos from text descriptions using Runway ML's video generation model.
    Supports various durations, aspect ratios, and motion levels."""
    
    inputs = {
        'prompt': {
            'type': 'string',
            'description': 'Text description of the video to generate',
            'required': True
        },
        'user_id': {
            'type': 'string',
            'description': 'User ID requesting the video generation',
            'required': True
        },
        'duration': {
            'type': 'integer',
            'description': 'Video duration in seconds: 5, 10, or 30',
            'default': 10,
            'nullable': True
        },
        'aspect_ratio': {
            'type': 'string',
            'description': 'Aspect ratio: 16:9, 9:16, or 1:1',
            'default': '16:9',
            'nullable': True
        },
        'motion': {
            'type': 'string',
            'description': 'Motion level: low, medium, or high',
            'default': 'medium',
            'nullable': True
        }
    }
    output_type = "string"

    def __init__(self, redis_client=None, storage_path=None):
        """
        Initialize VideoGenerationTool
        
        Args:
            redis_client: Redis client for caching and rate limiting
            storage_path: Path to store generated videos locally
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
        self.runway_api_key = os.getenv('RUNWAY_API_KEY')
        self.storage_path = storage_path or os.path.join(
            os.path.dirname(__file__), 'generated_videos'
        )
        
        # Create storage directory if it doesn't exist
        Path(self.storage_path).mkdir(parents=True, exist_ok=True)
        
        # Configuration
        self.config = {
            'model': 'gen3a',  # Runway ML model
            'api_base_url': 'https://api.runwayml.com/v1',
            'rate_limit_per_user': 3,  # videos per hour
            'rate_limit_per_day': 10,  # videos per day
            'save_locally': True,
            'tracking_enabled': True,
            'valid_durations': [5, 10, 30],
            'valid_aspect_ratios': ['16:9', '9:16', '1:1'],
            'valid_motions': ['low', 'medium', 'high'],
            'polling_interval': 5,  # seconds between status checks
            'max_polling_time': 600  # 10 minutes max wait
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

    def _validate_parameters(self, duration: int, aspect_ratio: str, motion: str) -> Optional[str]:
        """Validate input parameters"""
        if duration not in self.config['valid_durations']:
            return f"Invalid duration '{duration}'. Valid durations: {', '.join(map(str, self.config['valid_durations']))} seconds"
        
        if aspect_ratio not in self.config['valid_aspect_ratios']:
            return f"Invalid aspect ratio '{aspect_ratio}'. Valid ratios: {', '.join(self.config['valid_aspect_ratios'])}"
        
        if motion not in self.config['valid_motions']:
            return f"Invalid motion level '{motion}'. Valid levels: {', '.join(self.config['valid_motions'])}"
        
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

    def _track_video_generation(self, user_id: str, prompt: str, video_url: Optional[str], 
                               duration: int, aspect_ratio: str, motion: str, 
                               request_id: str = None) -> str:
        """Track generated videos for analytics and retrieval"""
        tracking_id = hashlib.md5(
            f"{user_id}:{prompt}:{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]
        
        tracking_data = {
            'tracking_id': tracking_id,
            'user_id': user_id,
            'prompt': prompt,
            'video_url': video_url,
            'request_id': request_id,
            'duration': duration,
            'aspect_ratio': aspect_ratio,
            'motion': motion,
            'timestamp': datetime.now().isoformat(),
            'model': self.config['model']
        }
        
        # Store in Redis for quick retrieval (7 days expiration)
        self.redis.setex(
            f"video:track:{tracking_id}",
            86400 * 7,
            json.dumps(tracking_data)
        )
        
        logger.info(f"Video generation tracked: {tracking_id}")
        return tracking_id

    def _save_video_locally(self, user_id: str, video_url: str, tracking_id: str) -> Optional[str]:
        """
        Download and save video locally
        
        Args:
            user_id: User ID
            video_url: URL of the generated video
            tracking_id: Tracking ID for the generation request
            
        Returns:
            Local file path or None if save fails
        """
        try:
            # Download video with extended timeout
            response = requests.get(video_url, timeout=120)
            response.raise_for_status()
            
            # Create user-specific directory
            user_dir = os.path.join(self.storage_path, user_id)
            Path(user_dir).mkdir(parents=True, exist_ok=True)
            
            # Save with tracking ID
            filename = f"{tracking_id}.mp4"
            filepath = os.path.join(user_dir, filename)
            
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"Video saved locally: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error saving video locally: {e}")
            return None

    def _generate_with_runway(self, prompt: str, duration: int, aspect_ratio: str, 
                             motion: str) -> Optional[Dict[str, Any]]:
        """
        Call Runway ML API to generate video
        
        Args:
            prompt: Text description
            duration: Video duration in seconds
            aspect_ratio: Aspect ratio (16:9, 9:16, 1:1)
            motion: Motion level (low, medium, high)
            
        Returns:
            Dict with request_id and status, or None if generation fails
        """
        try:
            headers = {
                'Authorization': f'Bearer {self.runway_api_key}',
                'Content-Type': 'application/json'
            }
            
            # Map motion levels to Runway parameters
            motion_params = {
                'low': 0.3,
                'medium': 0.6,
                'high': 0.9
            }
            
            payload = {
                'model': self.config['model'],
                'promptText': prompt,
                'duration': duration,
                'aspectRatio': aspect_ratio,
                'motionScore': motion_params.get(motion, 0.6),
                'watermark': False
            }
            
            logger.info(f"Initiating video generation with Runway ML")
            logger.debug(f"Prompt: {prompt[:100]}... | Duration: {duration}s | Aspect: {aspect_ratio}")
            
            # Create generation request
            response = requests.post(
                f"{self.config['api_base_url']}/image_to_video",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            request_id = result.get('id')
            if request_id:
                logger.info(f"Video generation request created: {request_id}")
                return {'request_id': request_id, 'status': 'processing'}
            else:
                logger.error(f"No request ID in response: {result}")
                return None
            
        except Exception as e:
            logger.error(f"Error generating video with Runway ML: {e}")
            return None

    def _poll_video_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """
        Poll Runway ML API for video generation status
        
        Args:
            request_id: Request ID from generation request
            
        Returns:
            Dict with status and video_url if complete, or None if failed
        """
        try:
            headers = {
                'Authorization': f'Bearer {self.runway_api_key}'
            }
            
            start_time = time.time()
            
            while time.time() - start_time < self.config['max_polling_time']:
                response = requests.get(
                    f"{self.config['api_base_url']}/tasks/{request_id}",
                    headers=headers,
                    timeout=10
                )
                
                response.raise_for_status()
                result = response.json()
                status = result.get('status')
                
                logger.debug(f"Video generation status: {status}")
                
                if status == 'SUCCEEDED':
                    video_url = result.get('output', [{}])[0].get('url')
                    if video_url:
                        logger.info(f"Video generation completed: {request_id}")
                        return {'status': 'completed', 'video_url': video_url}
                
                elif status == 'FAILED':
                    error_msg = result.get('error', 'Unknown error')
                    logger.error(f"Video generation failed: {error_msg}")
                    return {'status': 'failed', 'error': error_msg}
                
                # Wait before next poll
                time.sleep(self.config['polling_interval'])
            
            logger.error(f"Video generation polling timeout: {request_id}")
            return {'status': 'timeout'}
            
        except Exception as e:
            logger.error(f"Error polling video status: {e}")
            return None

    def forward(self, prompt: str, user_id: str, duration: int = 10, 
               aspect_ratio: str = '16:9', motion: str = 'medium') -> str:
        """
        Generate video from text prompt
        
        Args:
            prompt: Text description of desired video
            user_id: User requesting video generation
            duration: Video duration in seconds (5, 10, or 30)
            aspect_ratio: Aspect ratio (16:9, 9:16, 1:1)
            motion: Motion level (low, medium, high)
            
        Returns:
            Response string with video URL and tracking information
        """
        try:
            # Validate parameters
            validation_error = self._validate_parameters(duration, aspect_ratio, motion)
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
            
            # Generate video
            gen_result = self._generate_with_runway(prompt, duration, aspect_ratio, motion)
            if not gen_result or not gen_result.get('request_id'):
                return "❌ Failed to initiate video generation. Please try again."
            
            request_id = gen_result['request_id']
            
            # Track generation (initially without URL)
            tracking_id = self._track_video_generation(
                user_id, prompt, None, duration, aspect_ratio, motion, request_id
            )
            
            # Poll for completion
            status_result = self._poll_video_status(request_id)
            if not status_result:
                return "❌ Error checking video generation status."
            
            if status_result['status'] == 'failed':
                return f"❌ Video generation failed: {status_result.get('error', 'Unknown error')}"
            
            if status_result['status'] == 'timeout':
                return "❌ Video generation took too long. Please try again later."
            
            if status_result['status'] != 'completed':
                return "❌ Unexpected status during video generation."
            
            video_url = status_result.get('video_url')
            if not video_url:
                return "❌ Video generation completed but no URL provided."
            
            # Update tracking with video URL
            tracking_data = json.loads(self.redis.get(f"video:track:{tracking_id}"))
            tracking_data['video_url'] = video_url
            self.redis.setex(
                f"video:track:{tracking_id}",
                86400 * 7,
                json.dumps(tracking_data)
            )
            
            # Update rate limits
            self._update_rate_limit(user_id, 1)
            
            # Save locally if enabled
            local_path = None
            if self.config['save_locally']:
                local_path = self._save_video_locally(user_id, video_url, tracking_id)
            
            # Build response
            response = f"✅ Successfully generated video\n\n"
            response += f"📋 Prompt: {prompt}\n"
            response += f"🎬 Settings: {duration}s • {aspect_ratio} • {motion} motion\n"
            response += f"🆔 Tracking ID: {tracking_id}\n"
            response += f"📌 Request ID: {request_id}\n\n"
            response += f"🎥 Generated Video:\n"
            response += f"  URL: {video_url}\n"
            
            if local_path:
                response += f"  Local: {local_path}\n"
            
            return response
            
        except Exception as e:
            logger.error(f"Error in video generation: {e}", exc_info=True)
            return f"❌ Error generating video: {str(e)}"

    def get_generation_history(self, user_id: str, limit: int = 10) -> Dict[str, Any]:
        """
        Retrieve video generation history for a user
        
        Args:
            user_id: User ID
            limit: Maximum number of records to return
            
        Returns:
            Dictionary with generation history
        """
        try:
            pattern = f"video:track:*"
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

    def delete_video(self, tracking_id: str) -> bool:
        """Delete a generated video"""
        try:
            tracking_data = self.redis.get(f"video:track:{tracking_id}")
            if not tracking_data:
                return False
            
            data = json.loads(tracking_data)
            user_id = data.get('user_id')
            
            # Delete local file
            filename = f"{tracking_id}.mp4"
            filepath = os.path.join(self.storage_path, user_id, filename)
            
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"Deleted video: {filepath}")
            
            # Remove tracking data
            self.redis.delete(f"video:track:{tracking_id}")
            
            return True
        except Exception as e:
            logger.error(f"Error deleting video: {e}")
            return False
