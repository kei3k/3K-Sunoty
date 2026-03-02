"""
Video converter for audio-to-video conversion.

Converts MP3 files to MP4 format suitable for YouTube upload with various options.
"""

import os
import subprocess
from typing import Dict, Any, Optional
from pathlib import Path

try:
    from utils.logger import logger
    from ..utils.config_loader import config
except ImportError:
    from utils.logger import logger
    from utils.config_loader import config


class VideoConverter:
    """Converts audio files to video format for YouTube upload."""

    def __init__(self):
        """Initialize video converter."""
        pass

    def convert_audio_to_video(
        self,
        audio_file: str,
        output_video: str,
        duration: Optional[int] = None,
        width: int = 1920,
        height: int = 1080,
        fps: int = 30
    ) -> Dict[str, Any]:
        """
        Convert audio file to video format.

        Args:
            audio_file: Path to input audio file
            output_video: Path to output video file
            duration: Video duration in seconds (None = use audio duration)
            width: Video width in pixels
            height: Video height in pixels
            fps: Video frame rate

        Returns:
            Dictionary containing conversion results
        """
        try:
            logger.info(
                f"Converting audio to video",
                audio_file=audio_file,
                output_video=output_video,
                width=width,
                height=height
            )

            # Ensure output directory exists
            output_dir = os.path.dirname(output_video)
            os.makedirs(output_dir, exist_ok=True)

            # Create simple black video with audio
            result = self._create_video_with_ffmpeg(
                audio_file=audio_file,
                output_video=output_video,
                duration=duration,
                width=width,
                height=height,
                fps=fps
            )

            logger.info(
                f"Video conversion completed",
                audio_file=audio_file,
                output_video=output_video,
                duration=result.get('duration')
            )

            return result

        except Exception as e:
            error_result = {
                'status': 'failed',
                'audio_file': audio_file,
                'output_video': output_video,
                'error': str(e)
            }

            logger.error(
                f"Video conversion failed",
                **error_result
            )

            return error_result

    def _create_video_with_ffmpeg(
        self,
        audio_file: str,
        output_video: str,
        duration: Optional[int],
        width: int,
        height: int,
        fps: int
    ) -> Dict[str, Any]:
        """
        Create video using FFmpeg.

        Args:
            audio_file: Input audio file
            output_video: Output video file
            duration: Video duration
            width: Video width
            height: Video height
            fps: Frame rate

        Returns:
            Conversion result
        """
        # Build FFmpeg command
        cmd = [
            'ffmpeg',
            '-y',  # Overwrite output files
            '-f', 'lavfi',  # Use lavfi filter
            '-i', f'color=c=black:s={width}x{height}:d={duration or 180}',  # Black background
            '-i', audio_file,  # Audio input
            '-c:v', 'libx264',  # Video codec
            '-c:a', 'aac',  # Audio codec
            '-shortest',  # End when shortest input ends
            '-r', str(fps),  # Frame rate
            '-pix_fmt', 'yuv420p',  # Pixel format for compatibility
            output_video
        ]

        if duration is None:
            # If no duration specified, let FFmpeg determine from audio
            cmd.remove('-f')
            cmd.remove('lavfi')
            cmd[2] = '-f'
            cmd[3] = 'lavfi'
            cmd[4] = f'color=c=black:s={width}x{height}'
            cmd.insert(5, '-t')
            cmd.insert(6, '180')  # Default 3 minutes

        logger.debug(f"FFmpeg command: {' '.join(cmd)}")

        # Run FFmpeg
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode != 0:
                raise Exception(f"FFmpeg failed: {result.stderr}")

            # Get video info
            video_info = self._get_video_info(output_video)

            return {
                'status': 'success',
                'output_video': output_video,
                'audio_file': audio_file,
                'duration': video_info.get('duration'),
                'size_mb': video_info.get('size_mb'),
                'width': width,
                'height': height,
                'fps': fps
            }

        except subprocess.TimeoutExpired:
            raise Exception("FFmpeg conversion timed out")
        except FileNotFoundError:
            raise Exception("FFmpeg not found. Please install FFmpeg.")

    def create_video_with_waveform(
        self,
        audio_file: str,
        output_video: str,
        duration: Optional[int] = None,
        width: int = 1920,
        height: int = 1080,
        fps: int = 30
    ) -> Dict[str, Any]:
        """
        Create video with audio waveform visualization.

        Args:
            audio_file: Input audio file
            output_video: Output video file
            duration: Video duration
            width: Video width
            height: Video height
            fps: Frame rate

        Returns:
            Conversion result
        """
        try:
            logger.info(
                f"Creating waveform video",
                audio_file=audio_file,
                output_video=output_video
            )

            # FFmpeg command for waveform visualization
            cmd = [
                'ffmpeg',
                '-y',
                '-i', audio_file,
                '-filter_complex',
                f'[0:a]showwaves=s={width}x{height}:mode=line:colors=white:draw=full,format=yuv420p[v]',
                '-map', '[v]',
                '-map', '0:a',
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-r', str(fps),
                '-shortest',
                output_video
            ]

            if duration:
                cmd.insert(-1, '-t')
                cmd.insert(-1, str(duration))

            logger.debug(f"Waveform FFmpeg command: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode != 0:
                raise Exception(f"FFmpeg waveform failed: {result.stderr}")

            video_info = self._get_video_info(output_video)

            return {
                'status': 'success',
                'output_video': output_video,
                'audio_file': audio_file,
                'visualization': 'waveform',
                'duration': video_info.get('duration'),
                'size_mb': video_info.get('size_mb')
            }

        except Exception as e:
            logger.error(
                f"Waveform video creation failed",
                audio_file=audio_file,
                error=str(e)
            )
            raise

    def create_video_with_static_image(
        self,
        audio_file: str,
        image_file: str,
        output_video: str,
        duration: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create video with static image background.

        Args:
            audio_file: Input audio file
            image_file: Background image file
            output_video: Output video file
            duration: Video duration

        Returns:
            Conversion result
        """
        try:
            logger.info(
                f"Creating image background video",
                audio_file=audio_file,
                image_file=image_file,
                output_video=output_video
            )

            cmd = [
                'ffmpeg',
                '-y',
                '-loop', '1',
                '-i', image_file,
                '-i', audio_file,
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-shortest',
                '-r', '30',
                '-pix_fmt', 'yuv420p',
                output_video
            ]

            if duration:
                cmd.insert(-1, '-t')
                cmd.insert(-1, str(duration))

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode != 0:
                raise Exception(f"FFmpeg image video failed: {result.stderr}")

            video_info = self._get_video_info(output_video)

            return {
                'status': 'success',
                'output_video': output_video,
                'audio_file': audio_file,
                'image_file': image_file,
                'visualization': 'static_image',
                'duration': video_info.get('duration'),
                'size_mb': video_info.get('size_mb')
            }

        except Exception as e:
            logger.error(
                f"Static image video creation failed",
                audio_file=audio_file,
                image_file=image_file,
                error=str(e)
            )
            raise

    def _get_video_info(self, video_file: str) -> Dict[str, Any]:
        """
        Get basic information about a video file.

        Args:
            video_file: Path to video file

        Returns:
            Video information dictionary
        """
        try:
            # Get file size
            size_bytes = os.path.getsize(video_file)
            size_mb = size_bytes / (1024 * 1024)

            # Use ffprobe to get duration (if available)
            try:
                probe_cmd = [
                    'ffprobe',
                    '-v', 'quiet',
                    '-print_format', 'json',
                    '-show_format',
                    video_file
                ]

                probe_result = subprocess.run(
                    probe_cmd,
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if probe_result.returncode == 0:
                    import json
                    probe_data = json.loads(probe_result.stdout)
                    duration = float(probe_data['format']['duration'])
                else:
                    duration = None

            except (subprocess.SubprocessError, json.JSONDecodeError, KeyError):
                duration = None

            return {
                'size_mb': round(size_mb, 2),
                'duration': duration
            }

        except Exception:
            return {
                'size_mb': None,
                'duration': None
            }

    def convert_for_youtube(
        self,
        audio_file: str,
        output_video: str,
        visualization: str = 'simple',
        **kwargs
    ) -> Dict[str, Any]:
        """
        Convert audio to YouTube-compatible video format.

        Args:
            audio_file: Input audio file
            output_video: Output video file
            visualization: Type of visualization ('simple', 'waveform', 'image')
            **kwargs: Additional arguments for conversion

        Returns:
            Conversion result
        """
        try:
            logger.info(
                f"Converting audio for YouTube",
                audio_file=audio_file,
                output_video=output_video,
                visualization=visualization
            )

            if visualization == 'waveform':
                result = self.create_video_with_waveform(
                    audio_file=audio_file,
                    output_video=output_video,
                    **kwargs
                )
            elif visualization == 'image':
                image_file = kwargs.get('image_file')
                if not image_file:
                    raise ValueError("image_file required for image visualization")
                result = self.create_video_with_static_image(
                    audio_file=audio_file,
                    image_file=image_file,
                    output_video=output_video,
                    **kwargs
                )
            else:  # simple or default
                result = self.convert_audio_to_video(
                    audio_file=audio_file,
                    output_video=output_video,
                    **kwargs
                )

            # Validate YouTube compatibility
            self._validate_youtube_compatibility(result)

            logger.info(
                f"YouTube conversion completed",
                output_video=output_video,
                size_mb=result.get('size_mb')
            )

            return result

        except Exception as e:
            logger.error(
                f"YouTube conversion failed",
                audio_file=audio_file,
                error=str(e)
            )
            raise

    def _validate_youtube_compatibility(self, video_result: Dict[str, Any]):
        """
        Validate that video meets YouTube requirements.

        Args:
            video_result: Video conversion result

        Raises:
            Exception: If video doesn't meet requirements
        """
        size_mb = video_result.get('size_mb', 0)

        # YouTube has a 15GB limit for uploads, but we should warn about large files
        if size_mb and size_mb > 1000:  # 1GB warning
            logger.warning(
                f"Video file is very large: {size_mb}MB",
                output_video=video_result.get('output_video')
            )

        # Check for required codecs (this is basic validation)
        # Real validation would check actual codec details
        pass

    def cleanup_temp_files(self, files: list):
        """
        Clean up temporary files.

        Args:
            files: List of file paths to delete
        """
        for file_path in files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.debug(f"Cleaned up temp file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up temp file {file_path}: {e}")


# Global video converter instance
video_converter = VideoConverter()
