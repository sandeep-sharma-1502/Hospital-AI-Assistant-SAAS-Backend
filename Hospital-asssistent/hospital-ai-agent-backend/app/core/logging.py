import logging
import sys
from typing import Any

# If you use Pydantic for settings, import your config here:
# from app.core.config import settings

def setup_logging():
    """
    Configures the global logging settings for the application.
    """
    
    # 1. Define the log level (Usually 'INFO' or 'DEBUG')
    log_level = logging.INFO 
    
    # 2. Choose the format
    # Simple, readable format for local development
    log_format = (
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s "
        "(%(filename)s:%(lineno)d)"
    )

    # 3. Configure the Root Logger
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout)  # Standard output
        ],
    )

    # 4. Silence noisy third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

def get_logger(name: str) -> logging.Logger:
    """
    Utility function to get a named logger instance.
    """
    return logging.getLogger(name)