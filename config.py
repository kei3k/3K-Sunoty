"""
Configuration management
"""

import os
import json
import logging
from dotenv import load_dotenv

load_dotenv()

def setup_logging():
    """Setup logging configuration"""
    os.makedirs("logs", exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("logs/automation.log"),
            logging.StreamHandler()
        ]
    )

    return logging.getLogger(__name__)

def load_config():
    """Load configuration from environment"""
    return {
        'youtube_privacy': os.getenv('YOUTUBE_PRIVACY', 'private'),
        'max_retries': int(os.getenv('MAX_RETRIES', '3')),
        'headless_mode': os.getenv('HEADLESS_MODE', 'false').lower() == 'true'
    }
