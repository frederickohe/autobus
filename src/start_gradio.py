#!/usr/bin/env python
"""
Gradio UI launcher for the AutoBus AI Agent
This script initializes the AutoBus agent and starts an interactive Gradio interface.

Usage:
    python start_gradio.py
    
Optional environment variables:
    GRADIO_HOST: Host to run Gradio on (default: 127.0.0.1)
    GRADIO_PORT: Port to run Gradio on (default: 7860)
    FILE_UPLOAD_FOLDER: Path to folder for file uploads (optional)
"""

import os
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from core.agent.agent import AutoBus
from core.agent.Gradio_UI import GradioUI


def main():
    """Initialize and launch the Gradio UI for the AutoBus agent"""
    
    print("🚀 Initializing AutoBus AI Agent...")
    
    # Initialize the agent with prompts configuration
    prompts_path = str(Path(__file__).parent / "prompts.yaml")
    agent = AutoBus(db_session=None)
    
    print("✅ Agent initialized successfully!")
    print("🎨 Launching Gradio UI...")
    
    # Optional: Set up file upload folder
    file_upload_folder = os.getenv("FILE_UPLOAD_FOLDER")
    if file_upload_folder and not os.path.exists(file_upload_folder):
        os.makedirs(file_upload_folder)
        print(f"📁 Created file upload folder: {file_upload_folder}")
    
    # Initialize Gradio UI
    gradio_ui = GradioUI(
        agent=agent,
        file_upload_folder=file_upload_folder
    )
    
    # Get configuration from environment or use defaults
    host = os.getenv("GRADIO_HOST", "127.0.0.1")
    port = int(os.getenv("GRADIO_PORT", 7860))
    
    print(f"🌐 Starting Gradio UI on http://{host}:{port}")
    print("💬 You can now interact with your AI agent!")
    print("=" * 60)
    
    # Launch the Gradio interface
    gradio_ui.launch(
        server_name=host,
        server_port=port,
        share=False,  # Set to True if you want a public link
        debug=True,
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down Gradio UI...")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error launching Gradio UI: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
