#!/usr/bin/env python3
"""
Basic functionality tests for the Suno Remix Tool.

Tests core components without external API calls.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scripts.utils.config_loader import config
from scripts.utils.logger import logger
from scripts.modules.retry_manager import retry_manager


class TestBasicFunctionality(unittest.TestCase):
    """Test basic functionality of the remix tool."""

    def setUp(self):
        """Set up test environment."""
        self.test_song = "Test Song - Test Artist"

    def test_config_loading(self):
        """Test that configuration loads correctly."""
        # Test style templates
        style = config.get_style_template('lofi_chill')
        self.assertIsNotNone(style)
        self.assertEqual(style['id'], 'lofi_chill')
        self.assertIn('prompt_template', style)

        # Test default style
        default_style = config.get_default_style()
        self.assertEqual(default_style, 'lofi_chill')

    def test_parameter_calculation(self):
        """Test parameter calculation for attempts."""
        # Test first attempt
        params1 = retry_manager.calculate_attempt_parameters(1)
        self.assertEqual(params1['attempt'], 1)
        self.assertEqual(params1['pitch_shift'], 2)  # Default base pitch
        self.assertEqual(params1['tempo_multiplier'], 1.05)  # Default base tempo

        # Test second attempt
        params2 = retry_manager.calculate_attempt_parameters(2)
        self.assertEqual(params2['attempt'], 2)
        self.assertEqual(params2['pitch_shift'], 3)  # Base + 1
        self.assertEqual(params2['tempo_multiplier'], 1.07)  # Base + 0.02

    def test_should_retry_logic(self):
        """Test retry decision logic."""
        # Test no copyright - should not retry
        result = retry_manager.should_retry(1, {'has_copyright': False})
        self.assertFalse(result['should_retry'])
        self.assertEqual(result['reason'], 'no_copyright_detected')

        # Test high copyright risk - should retry
        result = retry_manager.should_retry(1, {
            'has_copyright': True,
            'claims': [{'matchPercent': 85}]
        })
        self.assertTrue(result['should_retry'])
        self.assertEqual(result['reason'], 'high_copyright_risk')

        # Test max attempts - should not retry
        result = retry_manager.should_retry(10, {
            'has_copyright': True,
            'claims': [{'matchPercent': 85}]
        })
        self.assertFalse(result['should_retry'])
        self.assertEqual(result['reason'], 'max_attempts_exceeded')

    def test_logger_initialization(self):
        """Test that logger initializes correctly."""
        # Test info logging
        logger.info("Test log message", test_key="test_value")

        # Test session logs
        logs = logger.get_session_logs()
        self.assertIsInstance(logs, list)
        self.assertGreater(len(logs), 0)

    def test_attempt_summary(self):
        """Test attempt summary generation."""
        # Mock attempts data
        attempts = [
            {
                'copyright_status': {'has_copyright': False},
                'pitch_shift': 2,
                'tempo_multiplier': 1.05
            },
            {
                'copyright_status': {'has_copyright': True, 'claims': [{'matchPercent': 80}]},
                'pitch_shift': 3,
                'tempo_multiplier': 1.07
            }
        ]

        summary = retry_manager.get_attempt_summary(attempts)

        self.assertEqual(summary['total_attempts'], 2)
        self.assertEqual(summary['successful_attempts'], 1)
        self.assertEqual(summary['failed_attempts'], 1)
        self.assertEqual(summary['success_rate'], 0.5)

    @patch('scripts.modules.suno_client.suno_client')
    def test_remix_generation_mock(self, mock_suno):
        """Test remix generation with mocked Suno client."""
        # Mock successful generation
        mock_suno.generate_remix_with_wait.return_value = {
            'status': 'success',
            'remix_file': '/tmp/test_remix.mp3',
            'generation_id': 'test_gen_123'
        }

        from scripts.modules.suno_client import suno_client

        # Test generation (will use mock)
        result = suno_client.generate_remix_with_wait(
            prompt="Test prompt",
            style_template={'id': 'test', 'model': 'chirp-v3', 'duration': '180s'},
            output_path='/tmp/test.mp3'
        )

        mock_suno.generate_remix_with_wait.assert_called_once()
        self.assertEqual(result['status'], 'success')

    def test_validation_functions(self):
        """Test input validation functions."""
        from scripts.modules.audio_processor import audio_processor

        # Test parameter validation
        self.assertTrue(audio_processor.validate_parameters(2, 1.05))
        self.assertFalse(audio_processor.validate_parameters(10, 1.05))  # Pitch too high
        self.assertFalse(audio_processor.validate_parameters(2, 1.5))    # Tempo too high


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete workflow."""

    def setUp(self):
        """Set up integration test environment."""
        # Create temporary directories
        self.temp_dir = tempfile.mkdtemp()
        self.music_dir = Path(self.temp_dir) / "music"
        self.video_dir = Path(self.temp_dir) / "videos"
        self.music_dir.mkdir()
        self.video_dir.mkdir()

    def tearDown(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('scripts.modules.suno_client.suno_client')
    @patch('scripts.modules.youtube_copyright_checker.youtube_checker')
    @patch('scripts.modules.video_converter.video_converter')
    def test_full_workflow_mock(self, mock_converter, mock_checker, mock_suno):
        """Test the full workflow with all components mocked."""
        # Mock all external dependencies
        mock_suno.generate_remix_with_wait.return_value = {
            'status': 'success',
            'remix_file': str(self.music_dir / 'test_remix.mp3'),
            'generation_id': 'test_gen_123'
        }

        mock_converter.convert_for_youtube.return_value = {
            'status': 'success',
            'output_video': str(self.video_dir / 'test_video.mp4')
        }

        mock_checker.upload_and_check_copyright.return_value = {
            'status': 'success',
            'copyright_status': {'has_copyright': False},
            'video_id': 'test_video_123'
        }

        # Import and test the main tool
        from scripts.scripts.main_remix_tool import SunoRemixTool

        tool = SunoRemixTool()
        tool.music_dir = self.music_dir
        tool.video_dir = self.video_dir

        result = tool.process_song("Test Song")

        # Verify the workflow completed
        self.assertEqual(result['status'], 'success')
        self.assertIn('final_remix', result)
        self.assertIn('total_attempts', result)


if __name__ == '__main__':
    # Set up basic environment for testing
    os.environ.setdefault('SUNO_API_KEY', 'test_key')
    os.environ.setdefault('YOUTUBE_API_KEY', 'test_key')

    unittest.main()
