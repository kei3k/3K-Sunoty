"""
Configuration loader for the Suno Remix Tool.

Handles loading environment variables and JSON configuration files.
"""

import os
import json
from typing import Dict, Any, Optional
from dotenv import load_dotenv


class ConfigLoader:
    """Loads and manages configuration settings from .env and JSON files."""

    def __init__(self, env_path: str = ".env", config_dir: str = "scripts/configs"):
        """
        Initialize configuration loader.

        Args:
            env_path: Path to .env file
            config_dir: Directory containing JSON config files
        """
        self.config_dir = config_dir
        self._configs = {}

        # Load environment variables
        load_dotenv(env_path)

        # Load JSON configs
        self._load_json_configs()

    def _load_json_configs(self):
        """Load all JSON configuration files from config directory."""
        config_files = [
            "remix_styles.json",
            "remix_settings.json"
        ]

        for config_file in config_files:
            config_path = os.path.join(self.config_dir, config_file)
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config_name = config_file.replace('.json', '')
                    self._configs[config_name] = json.load(f)

    def get_env_var(self, key: str, default: Any = None) -> Any:
        """
        Get environment variable.

        Args:
            key: Environment variable key
            default: Default value if not found

        Returns:
            Environment variable value
        """
        value = os.getenv(key, default)
        if value is not None:
            # Try to convert to appropriate type
            if isinstance(default, bool):
                return value.lower() in ('true', '1', 'yes', 'on')
            elif isinstance(default, int):
                try:
                    return int(value)
                except ValueError:
                    return default
            elif isinstance(default, float):
                try:
                    return float(value)
                except ValueError:
                    return default
        return value

    def get_config(self, config_name: str) -> Dict[str, Any]:
        """
        Get JSON configuration by name.

        Args:
            config_name: Configuration name (e.g., 'remix_styles')

        Returns:
            Configuration dictionary
        """
        return self._configs.get(config_name, {})

    def get_style_template(self, style_id: str) -> Optional[Dict[str, Any]]:
        """
        Get remix style template by ID.

        Args:
            style_id: Style ID (e.g., 'lofi_chill')

        Returns:
            Style template dictionary or None if not found
        """
        styles = self.get_config('remix_styles').get('styles', [])
        for style in styles:
            if style['id'] == style_id:
                return style
        return None

    def get_channel_settings(self, channel_id: str) -> Dict[str, Any]:
        """
        Get channel-specific settings.

        Args:
            channel_id: YouTube channel ID

        Returns:
            Channel settings dictionary
        """
        channels = self.get_config('remix_settings').get('channels', {})
        return channels.get(channel_id, {})

    def get_default_style(self) -> str:
        """
        Get default remix style.

        Returns:
            Default style ID
        """
        return self.get_config('remix_settings').get('default_style', 'lofi_chill')

    def get_test_upload_settings(self) -> Dict[str, Any]:
        """
        Get test upload settings for YouTube.

        Returns:
            Test upload settings dictionary
        """
        return self.get_config('remix_settings').get('test_upload_settings', {})

    # Environment variable getters with defaults
    @property
    def suno_api_key(self) -> str:
        return self.get_env_var('SUNO_API_KEY', '')

    @property
    def suno_account_id(self) -> str:
        return self.get_env_var('SUNO_ACCOUNT_ID', '')

    @property
    def youtube_api_key(self) -> str:
        return self.get_env_var('YOUTUBE_API_KEY', '')

    @property
    def youtube_channel_id(self) -> str:
        return self.get_env_var('YOUTUBE_CHANNEL_ID', '')

    @property
    def max_remix_attempts(self) -> int:
        return self.get_env_var('MAX_REMIX_ATTEMPTS', 10)

    @property
    def youtube_wait_time(self) -> int:
        return self.get_env_var('YOUTUBE_WAIT_TIME', 300)

    @property
    def retry_backoff(self) -> int:
        return self.get_env_var('RETRY_BACKOFF', 5)

    @property
    def min_pitch_shift(self) -> int:
        return self.get_env_var('MIN_PITCH_SHIFT', -5)

    @property
    def max_pitch_shift(self) -> int:
        return self.get_env_var('MAX_PITCH_SHIFT', 5)

    @property
    def min_tempo_multiplier(self) -> float:
        return self.get_env_var('MIN_TEMPO_MULTIPLIER', 0.85)

    @property
    def max_tempo_multiplier(self) -> float:
        return self.get_env_var('MAX_TEMPO_MULTIPLIER', 1.20)

    @property
    def copyright_match_threshold(self) -> int:
        return self.get_env_var('COPYRIGHT_MATCH_THRESHOLD', 75)

    @property
    def safe_match_threshold(self) -> int:
        return self.get_env_var('SAFE_MATCH_THRESHOLD', 50)


# Global config instance
config = ConfigLoader()
