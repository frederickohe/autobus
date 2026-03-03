"""
Image Generation Tool - Usage Examples

This file demonstrates various ways to use the ImageGenerationTool
"""

from core.agent.tools.generate_image.generate_image import ImageGenerationTool


def example_1_basic_generation():
    """Example 1: Basic image generation"""
    tool = ImageGenerationTool()
    
    response = tool.forward(
        prompt="A beautiful sunset over the ocean",
        user_id="user_123"
    )
    
    print("Basic Generation Response:")
    print(response)
    print("\n" + "="*80 + "\n")


def example_2_hd_multiple_images():
    """Example 2: Generate multiple HD images"""
    tool = ImageGenerationTool()
    
    response = tool.forward(
        prompt="A futuristic city with advanced technology and renewable energy",
        user_id="user_456",
        size="1792x1024",
        quality="hd",
        style="vivid",
        num_images=3
    )
    
    print("HD Multiple Images Response:")
    print(response)
    print("\n" + "="*80 + "\n")


def example_3_portrait_style():
    """Example 3: Portrait-oriented image"""
    tool = ImageGenerationTool()
    
    response = tool.forward(
        prompt="A serene portrait of a person meditating in nature",
        user_id="user_789",
        size="1024x1792",
        quality="standard",
        style="natural"
    )
    
    print("Portrait Style Response:")
    print(response)
    print("\n" + "="*80 + "\n")


def example_4_natural_style():
    """Example 4: Natural style image"""
    tool = ImageGenerationTool()
    
    response = tool.forward(
        prompt="A realistic photograph of a family enjoying a picnic in a park",
        user_id="user_101",
        size="1024x1024",
        quality="hd",
        style="natural",
        num_images=2
    )
    
    print("Natural Style Response:")
    print(response)
    print("\n" + "="*80 + "\n")


def example_5_check_history():
    """Example 5: Check generation history"""
    tool = ImageGenerationTool()
    
    history = tool.get_generation_history(user_id="user_123", limit=5)
    
    print("Generation History:")
    print(f"User: {history['user_id']}")
    print(f"Total Generations: {history['total']}")
    print("\nRecent Generations:")
    
    for i, gen in enumerate(history['generations'], 1):
        print(f"\n{i}. {gen['prompt'][:50]}...")
        print(f"   Time: {gen['timestamp']}")
        print(f"   Images: {gen['num_images']}")
        print(f"   Size: {gen['size']} | Quality: {gen['quality']} | Style: {gen['style']}")
        print(f"   Tracking ID: {gen['tracking_id']}")
    
    print("\n" + "="*80 + "\n")


def example_6_error_handling():
    """Example 6: Error handling"""
    tool = ImageGenerationTool()
    
    # Example 1: Too long prompt
    response = tool.forward(
        prompt="x" * 5000,  # Prompt too long
        user_id="user_202"
    )
    print("Error Handling - Long Prompt:")
    print(response)
    print("\n")
    
    # Example 2: Invalid size
    response = tool.forward(
        prompt="A cute cat",
        user_id="user_202",
        size="999x999"  # Invalid size
    )
    print("Error Handling - Invalid Size:")
    print(response)
    print("\n")
    
    # Example 3: Invalid number of images
    response = tool.forward(
        prompt="A dog running",
        user_id="user_202",
        num_images=10  # Too many images
    )
    print("Error Handling - Too Many Images:")
    print(response)
    print("\n" + "="*80 + "\n")


def example_7_rate_limiting():
    """Example 7: Check rate limiting status"""
    tool = ImageGenerationTool()
    user_id = "user_rate_test"
    
    # Check initial status
    status = tool._check_rate_limit(user_id)
    print(f"Initial Rate Limit Check: Allowed={status['allowed']}")
    
    # Make a request
    tool.forward(
        prompt="A beautiful landscape",
        user_id=user_id
    )
    
    # Check status after request
    status = tool._check_rate_limit(user_id)
    print(f"After 1 request: Allowed={status['allowed']}")
    print("\n" + "="*80 + "\n")


def example_8_with_agent():
    """Example 8: Integration with AutoBus agent"""
    from core.agent.agent import AutoBus
    
    # Initialize agent with database session if available
    autobus = AutoBus()
    
    # User message requesting image generation
    user_message = "Generate a beautiful image of a tropical beach with crystal clear water"
    
    # Process through agent
    response = autobus.process_user_message(
        userid="user_agent_123",
        message=user_message,
        agent_name="image-generator"
    )
    
    print("Agent Integration Response:")
    print(response)
    print("\n" + "="*80 + "\n")


def example_9_delete_image():
    """Example 9: Delete a generated image"""
    tool = ImageGenerationTool()
    
    # Generate an image first
    response = tool.forward(
        prompt="A test image",
        user_id="user_delete_test"
    )
    
    # Extract tracking ID from response
    import re
    match = re.search(r'Tracking ID: (\w+)', response)
    if match:
        tracking_id = match.group(1)
        
        # Delete the first image
        success = tool.delete_image(tracking_id, image_index=0)
        print(f"Image deletion: {'Success' if success else 'Failed'}")
    
    print("\n" + "="*80 + "\n")


def example_10_custom_config():
    """Example 10: Create tool with custom configuration"""
    import redis
    
    # Initialize with custom Redis client
    redis_client = redis.Redis(
        host='localhost',
        port=6379,
        password='autobus098',
        db=0,
        decode_responses=True
    )
    
    tool = ImageGenerationTool(
        redis_client=redis_client,
        storage_path="/custom/path/to/images"
    )
    
    response = tool.forward(
        prompt="A custom configured image",
        user_id="user_custom"
    )
    
    print("Custom Configuration Response:")
    print(response)
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    print("Image Generation Tool - Usage Examples\n")
    print("="*80 + "\n")
    
    # Run examples
    try:
        example_1_basic_generation()
        example_2_hd_multiple_images()
        example_3_portrait_style()
        example_4_natural_style()
        example_5_check_history()
        example_6_error_handling()
        example_7_rate_limiting()
        # example_8_with_agent()  # Uncomment to test agent integration
        # example_9_delete_image()  # Uncomment to test deletion
        # example_10_custom_config()  # Uncomment to test custom config
        
        print("\nAll examples completed!")
    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()
