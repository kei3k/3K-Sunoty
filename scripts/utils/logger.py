"""
Logging utility for the Suno Remix Tool.

Provides structured logging with different levels and file output.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path


class RemixLogger:
    """Structured logger for remix operations with JSON output."""

    def __init__(self, log_dir: str = "output/logs", log_level: str = "INFO"):
        """
        Initialize logger.

        Args:
            log_dir: Directory to store log files
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Set up logging
        self.logger = logging.getLogger('remix_tool')
        self.logger.setLevel(getattr(logging, log_level.upper()))

        # Remove existing handlers to avoid duplicates
        self.logger.handlers.clear()

        # Console handler
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        # File handler for general logs
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.log_dir / f"remix_tool_{timestamp}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(console_formatter)
        self.logger.addHandler(file_handler)

        self.current_session_logs = []

    def _log_structured(self, level: str, message: str, **kwargs):
        """
        Log structured data.

        Args:
            level: Log level
            message: Log message
            **kwargs: Additional structured data
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'level': level,
            'message': message,
            **kwargs
        }

        self.current_session_logs.append(log_entry)

        # Log to standard logger
        getattr(self.logger, level.lower())(f"{message} - {kwargs}")

    def info(self, message: str, **kwargs):
        """Log info message."""
        self._log_structured('INFO', message, **kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self._log_structured('WARNING', message, **kwargs)

    def error(self, message: str, **kwargs):
        """Log error message."""
        self._log_structured('ERROR', message, **kwargs)

    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self._log_structured('DEBUG', message, **kwargs)

    def log_attempt(self, attempt_data: Dict[str, Any]):
        """
        Log a remix attempt with detailed metadata.

        Args:
            attempt_data: Dictionary containing attempt information
        """
        self.info(
            f"Remix attempt {attempt_data.get('attempt', '?')}",
            **attempt_data
        )

    def log_copyright_check(self, video_id: str, copyright_status: Dict[str, Any]):
        """
        Log copyright check results.

        Args:
            video_id: YouTube video ID
            copyright_status: Copyright check results
        """
        self.info(
            f"Copyright check for video {video_id}",
            video_id=video_id,
            **copyright_status
        )

    def log_suno_generation(self, song_name: str, style_id: str, suno_id: str, status: str):
        """
        Log Suno generation status.

        Args:
            song_name: Original song name
            style_id: Remix style used
            suno_id: Suno generation ID
            status: Generation status
        """
        self.info(
            f"Suno generation {status}",
            song_name=song_name,
            style_id=style_id,
            suno_id=suno_id,
            status=status
        )

    def save_session_log(self, song_name: str) -> str:
        """
        Save current session logs to JSON file.

        Args:
            song_name: Song name for filename

        Returns:
            Path to saved log file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_song_name = "".join(c for c in song_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        filename = f"remix_{timestamp}_{safe_song_name}.json"
        log_path = self.log_dir / filename

        with open(log_path, 'w') as f:
            json.dump(self.current_session_logs, f, indent=2)

        self.info(f"Session log saved to {log_path}")
        return str(log_path)

    def get_session_logs(self) -> list:
        """
        Get current session logs.

        Returns:
            List of log entries
        """
        return self.current_session_logs.copy()


# Global logger instance
logger = RemixLogger()
