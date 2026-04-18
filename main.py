import uvicorn
import os
from src.app import app
from src.config import settings

if __name__ == "__main__":
    # Enable reload in debug/development mode
    # Can be set via DEBUG=true env var or --dev flag
    is_dev = os.environ.get('DEBUG', 'false').lower() == 'true'
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=3090,
        reload=is_dev,
        reload_dirs=["src"],  # Watch only src directory for changes
        log_level="info"
    )