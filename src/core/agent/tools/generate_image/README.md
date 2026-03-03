# Image Generation Tool

A comprehensive image generation tool using OpenAI's DALL-E 3 API integrated with the AutoBus agent system.

## Features

- **DALL-E 3 Integration**: Generate high-quality images from text prompts
- **Multiple Sizes**: Support for 1024x1024, 1792x1024, and 1024x1792 pixel images
- **Quality Options**: Standard or HD quality generation
- **Style Presets**: Natural or vivid image styles
- **Batch Generation**: Generate multiple images (1-4) per request
- **Rate Limiting**: Hourly (10 images) and daily (50 images) limits per user
- **Local Storage**: Automatically saves generated images locally
- **Tracking**: Track all image generations with unique IDs
- **History**: Retrieve user's image generation history

## Usage

### Basic Usage in Agent

The image generation tool is automatically integrated into the AutoBus agent:

```python
# Message to agent that triggers image generation
"Generate an image of a futuristic city at sunset with flying cars"
```

### Direct Tool Usage

```python
from core.agent.tools.generate_image.generate_image import ImageGenerationTool

# Initialize the tool
image_tool = ImageGenerationTool()

# Generate a single image
response = image_tool.forward(
    prompt="A serene mountain landscape with a clear blue sky",
    user_id="user_123"
)

# Generate multiple images with custom settings
response = image_tool.forward(
    prompt="A futuristic robot assistant in a modern office",
    user_id="user_123",
    size="1792x1024",
    quality="hd",
    style="vivid",
    num_images=2
)

print(response)
```

### Configuration

The tool respects the following environment variables:

```bash
OPENAI_API_KEY=your-openai-api-key
REDIS_HOST=localhost
REDIS_PORT=6379
```

### Parameters

- **prompt** (required): Text description of the image (max 4000 characters)
- **user_id** (required): User requesting the generation
- **size** (optional): Image dimensions
  - `1024x1024` (default)
  - `1792x1024` (landscape)
  - `1024x1792` (portrait)
- **quality** (optional): `standard` (default) or `hd`
- **style** (optional): `natural` (default) or `vivid`
- **num_images** (optional): Number of images to generate (1-4, default: 1)

### Response Format

Successful response includes:
- ✅ Confirmation message
- 📋 Original prompt
- 🎨 Settings used
- 🆔 Tracking ID for future reference
- 🖼️ Generated image URLs
- 📁 Local file paths (if saved)

Example:
```
✅ Successfully generated 2 image(s)

📋 Prompt: A serene mountain landscape...
🎨 Settings: 1792x1024 • hd • vivid
🆔 Tracking ID: a1b2c3d4e5f6g7h8

🖼️ Generated Images:

Image 1:
  URL: https://oaidalleapiproduc.blob.core.windows.net/...
  Local: /path/to/storage/user_123/a1b2c3d4e5f6g7h8_0.png

Image 2:
  URL: https://oaidalleapiproduc.blob.core.windows.net/...
  Local: /path/to/storage/user_123/a1b2c3d4e5f6g7h8_1.png
```

## Advanced Features

### Retrieve Generation History

```python
history = image_tool.get_generation_history(user_id="user_123", limit=10)
print(f"Total generations: {history['total']}")
for gen in history['generations']:
    print(f"- {gen['prompt']}: {len(gen['image_urls'])} images")
```

### Delete Generated Images

```python
success = image_tool.delete_image(tracking_id="a1b2c3d4e5f6g7h8", image_index=0)
```

### Check Rate Limits

```python
status = image_tool._check_rate_limit(user_id="user_123")
if status['allowed']:
    print("User can generate images")
else:
    print(f"Rate limit: {status['reason']}")
```

## Rate Limiting

- **Hourly**: 10 images per user per hour
- **Daily**: 50 images per user per day

When rate limit is exceeded, the tool returns an informative error message with current usage stats.

## Storage

By default, generated images are stored in:
```
src/core/agent/tools/generate_image/generated_images/{user_id}/
```

Images are named with their tracking ID for easy reference.

## Error Handling

The tool provides clear error messages for:
- Invalid parameters (size, quality, style)
- Rate limit exceeded
- Empty or too-long prompts
- API errors
- Network issues

## Integration Example

To fully integrate with your agent:

```python
from core.agent.agent import AutoBus

# Initialize agent
autobus = AutoBus()

# User requests image generation
response = autobus.process_user_message(
    userid="user_123",
    message="Create an image of a peaceful zen garden",
    agent_name="image-generator"
)

print(response)  # Shows generated image URLs
```

## Troubleshooting

### "OpenAI API Key not found"
- Ensure `OPENAI_API_KEY` environment variable is set
- Verify the API key is valid and has image generation permissions

### "Rate limit exceeded"
- Wait before requesting more images
- Check hourly/daily limits: `image_tool._check_rate_limit(user_id)`

### "Redis connection failed"
- Ensure Redis is running
- Check `REDIS_HOST` and `REDIS_PORT` environment variables

### Images not saving locally
- Check write permissions for storage directory
- Verify storage path exists and is writable
- Set `save_locally: true` in config

## Costs

Each image generation call costs credits from your OpenAI account:
- **DALL-E 3 Standard**: ~$0.04 per image
- **DALL-E 3 HD**: ~$0.08 per image (for 1024x1792 or 1792x1024)
- **DALL-E 3 HD**: ~$0.12 per image (for 1024x1024)

Monitor your usage to avoid unexpected charges.
