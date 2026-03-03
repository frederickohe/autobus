# Image Generation Tool - Quick Setup Guide

## ✅ What's Been Created

I've built a complete image generation tool integrated with your AutoBus agent system. Here's what was implemented:

### Files Created:
1. **generate_image.py** - Main tool implementation with OpenAI DALL-E 3 integration
2. **__init__.py** - Module initialization
3. **README.md** - Comprehensive documentation
4. **examples.py** - 10 ready-to-use examples

### Files Modified:
1. **agent.py** - Updated to use the new ImageGenerationTool instead of generic loader

## 🚀 Quick Start

### 1. Ensure Environment Variables

Make sure your `.env` file has:
```bash
OPENAI_API_KEY=your-openai-api-key
REDIS_HOST=localhost
REDIS_PORT=6379
```

### 2. Use with Your Agent

The tool is automatically available in your AutoBus agent:

```python
from core.agent.agent import AutoBus

autobus = AutoBus()

# User can request image generation naturally
response = autobus.process_user_message(
    userid="user_123",
    message="Generate a beautiful sunset over mountains",
    agent_name="autobus"
)
```

### 3. Direct Tool Usage

```python
from core.agent.tools.generate_image.generate_image import ImageGenerationTool

tool = ImageGenerationTool()

# Basic generation
response = tool.forward(
    prompt="A futuristic city",
    user_id="user_123"
)

# Advanced options
response = tool.forward(
    prompt="A serene zen garden",
    user_id="user_123",
    size="1792x1024",      # Landscape
    quality="hd",           # Higher quality
    style="natural",        # Natural or vivid
    num_images=2            # Generate 2 images
)
```

## 📋 Key Features

✅ **DALL-E 3 Integration** - OpenAI's latest image model
✅ **Multiple Sizes** - 1024x1024, 1792x1024 (landscape), 1024x1792 (portrait)
✅ **Quality Options** - Standard or HD
✅ **Style Presets** - Natural or Vivid
✅ **Batch Generation** - 1-4 images per request
✅ **Rate Limiting** - 10/hour, 50/day per user
✅ **Local Storage** - Auto-save generated images
✅ **Tracking** - Unique IDs for all generations
✅ **History** - Access user's generation history
✅ **Error Handling** - Clear error messages

## 🔧 Configuration

The tool auto-configures with sensible defaults:

```python
{
    'model': 'dall-e-3',
    'rate_limit_per_user': 10,      # images/hour
    'rate_limit_per_day': 50,       # images/day
    'save_locally': True,
    'tracking_enabled': True,
    'valid_sizes': {
        'dall-e-3': ['1024x1024', '1792x1024', '1024x1792']
    }
}
```

## 📊 Response Example

```
✅ Successfully generated 2 image(s)

📋 Prompt: A futuristic city with flying cars
🎨 Settings: 1792x1024 • hd • vivid
🆔 Tracking ID: a1b2c3d4e5f6g7h8

🖼️ Generated Images:

Image 1:
  URL: https://oaidalleapiproduc.blob.core.windows.net/...
  Local: src/core/agent/tools/generate_image/generated_images/user_123/a1b2c3d4e5f6g7h8_0.png

Image 2:
  URL: https://oaidalleapiproduc.blob.core.windows.net/...
  Local: src/core/agent/tools/generate_image/generated_images/user_123/a1b2c3d4e5f6g7h8_1.png
```

## 💰 Pricing

OpenAI charges per image:
- **DALL-E 3 Standard**: ~$0.04 per image
- **DALL-E 3 HD**: ~$0.08-$0.12 per image (depending on size)

Monitor your usage with rate limit checks:
```python
status = tool._check_rate_limit(user_id="user_123")
print(f"Rate limit ok: {status['allowed']}")
```

## 🧪 Run Examples

Test the tool with provided examples:
```bash
# Make sure you're in the project directory
cd autobus

# Activate virtual environment (if using venv)
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Run examples
python -c "from src.core.agent.tools.generate_image.examples import *; example_1_basic_generation()"
```

## 📚 More Information

For detailed information:
- Read [README.md](README.md) in the generate_image folder
- Review [examples.py](examples.py) for all usage patterns
- Check the source code [generate_image.py](generate_image.py) for all available methods

## 🐛 Troubleshooting

### API Key Error
```python
# Make sure OPENAI_API_KEY is set
import os
print(os.getenv('OPENAI_API_KEY'))  # Should print your key, not None
```

### Redis Connection Error
```python
# Verify Redis is running
# Check environment variables
os.getenv('REDIS_HOST')  # Should be 'localhost' or your Redis host
os.getenv('REDIS_PORT')  # Should be '6379' or your Redis port
```

### Rate Limit Tips
```python
# Check current usage
status = tool._check_rate_limit(user_id)
if not status['allowed']:
    print(f"Wait before requesting more: {status['reason']}")
```

## 🎯 Next Steps

1. Test with a simple prompt: `"A cute cat"`
2. Try different sizes and qualities
3. Monitor your API usage and costs
4. Integrate with your frontend/UI
5. Add custom prompt templates for your use cases

## 📝 Notes

- Images are stored locally and remain accessible
- Generation history is tracked in Redis
- Rate limits reset hourly/daily
- Each tracking ID uniquely identifies a generation request
- All errors are handled gracefully with user-friendly messages

Enjoy generating amazing images! 🎨
