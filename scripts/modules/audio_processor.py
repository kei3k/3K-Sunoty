"""
Audio processor for pitch and tempo manipulation.

Uses librosa for audio analysis and modification to create "transformative" versions
of songs for copyright avoidance.
"""

import os
import librosa
import soundfile as sf
import numpy as np
from typing import Dict, Any, Tuple, Optional

try:
    from utils.logger import logger
    from utils.config_loader import config
except ImportError:
    from utils.logger import logger
    from utils.config_loader import config


class AudioProcessor:
    """Processes audio files with pitch and tempo modifications."""

    def __init__(self, sample_rate: int = 22050):
        """Initialize audio processor."""
        self.sample_rate = sample_rate

    def analyze_audio(self, mp3_path: str) -> Dict[str, Any]:
        """
        Extract audio properties for analysis.

        Args:
            mp3_path: Path to MP3 file

        Returns:
            Dictionary with audio properties
        """
        try:
            y, sr = librosa.load(mp3_path, sr=self.sample_rate)

            # Extract BPM - try different methods for compatibility
            try:
                # For newer librosa versions
                bpm = float(librosa.beat.tempo(y=y, sr=sr))
            except TypeError:
                try:
                    # For older librosa versions
                    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
                    bpm = float(librosa.beat.tempo(onset_envelope=onset_env, sr=sr))
                except TypeError:
                    # Fallback
                    bpm = 120.0  # Default BPM

            # Extract key (simplified)
            try:
                chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
                key_estimate = np.argmax(np.mean(chroma, axis=1))
                keys = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
                key = keys[key_estimate]
            except Exception:
                key = "C"  # Default key

            duration = float(librosa.get_duration(y=y, sr=sr))

            return {
                "bpm": bpm,
                "key": key,
                "duration": duration,
                "sample_rate": sr
            }

        except Exception as e:
            logger.error(f"Failed to analyze audio: {e}")
            return {
                "bpm": 120.0,  # Default values
                "key": "C",
                "duration": 180.0,
                "sample_rate": self.sample_rate
            }

    def modify_pitch_tempo(
        self,
        mp3_path: str,
        pitch_shift: int = 0,
        tempo_multiplier: float = 1.0,
        output_path: str = None
    ) -> str:
        """
        Modify pitch and tempo of audio file.

        Args:
            mp3_path: Input MP3 file path
            pitch_shift: Semitones to shift pitch (+/-)
            tempo_multiplier: Tempo multiplier
            output_path: Output WAV file path

        Returns:
            Path to modified audio file
        """
        try:
            if output_path is None:
                output_path = mp3_path.replace(".mp3", "_modified.wav")

            # Load audio
            y, sr = librosa.load(mp3_path, sr=self.sample_rate)

            print(f"Processing audio: pitch {pitch_shift:+.1f}, tempo {tempo_multiplier:.2f}x")

            # Apply pitch shift
            if pitch_shift != 0:
                y = librosa.effects.pitch_shift(y, sr=sr, n_steps=pitch_shift)

            # Apply tempo change
            if tempo_multiplier != 1.0:
                y = librosa.effects.time_stretch(y, rate=tempo_multiplier)

            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Save to WAV
            sf.write(output_path, y, sr)
            print(f"[OK] Modified audio saved: {output_path}")

            return output_path

        except Exception as e:
            logger.error(f"Failed to modify audio: {e}")
            raise

    def validate_parameters(self, pitch_shift: int, tempo_multiplier: float) -> bool:
        """
        Validate pitch and tempo parameters.

        Args:
            pitch_shift: Pitch shift in semitones
            tempo_multiplier: Tempo multiplier

        Returns:
            True if parameters are valid
        """
        try:
            # Check pitch shift bounds
            if not isinstance(pitch_shift, (int, float)):
                return False
            if not (config.min_pitch_shift <= pitch_shift <= config.max_pitch_shift):
                return False

            # Check tempo multiplier bounds
            if not isinstance(tempo_multiplier, (int, float)):
                return False
            if not (config.min_tempo_multiplier <= tempo_multiplier <= config.max_tempo_multiplier):
                return False

            return True

        except Exception as e:
            logger.error(f"Parameter validation failed: {e}")
            return False

    def get_waveform_data(self, audio_path: str, max_points: int = 1000) -> list:
        """
        Get waveform data for visualization.

        Args:
            audio_path: Path to audio file
            max_points: Maximum number of data points

        Returns:
            List of waveform amplitudes
        """
        try:
            y, sr = librosa.load(audio_path, sr=self.sample_rate)

            # Downsample to max_points
            indices = np.linspace(0, len(y) - 1, max_points, dtype=int)
            waveform = y[indices].tolist()

            return waveform

        except Exception as e:
            logger.error(f"Failed to get waveform: {e}")
            return []


# Global audio processor instance
audio_processor = AudioProcessor()
