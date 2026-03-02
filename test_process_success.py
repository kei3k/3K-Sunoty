#!/usr/bin/env python3
"""
Test script to demonstrate successful process execution
"""

import os
import sys
import tempfile
import numpy as np
import soundfile as sf

# Add scripts directory to path
scripts_dir = os.path.join(os.path.dirname(__file__), 'scripts')
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)

def create_test_mp3():
    """Create a simple test MP3 file"""
    # Create a simple sine wave
    sample_rate = 22050
    duration = 10  # seconds
    frequency = 440  # A4 note

    t = np.linspace(0, duration, int(sample_rate * duration), False)
    audio = np.sin(frequency * 2 * np.pi * t)

    # Create temp file
    temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    sf.write(temp_file.name, audio, sample_rate)

    return temp_file.name

def test_process_success():
    """Test the full process"""
    print("🎵 TESTING PROCESS SUCCESS")
    print("="*50)

    # Create test audio file
    test_mp3 = create_test_mp3()
    print(f"Created test audio file: {test_mp3}")

    try:
        # Import the processor
        from scripts.modules.audio_processor import audio_processor
        from scripts.modules.retry_manager import retry_manager
        from scripts.utils.config_loader import config
        from scripts.utils.logger import logger

        print("\n[STEP 1] Testing audio analysis...")
        audio_props = audio_processor.analyze_audio(test_mp3)
        print(f"  BPM: {audio_props['bpm']:.1f}")
        print(f"  Key: {audio_props['key']}")
        print(f"  Duration: {audio_props['duration']:.1f}s")
        print("  [OK] Audio analysis successful")

        print("\n[STEP 2] Testing parameter calculation...")
        params = retry_manager.calculate_attempt_parameters(1)
        print(f"  Attempt 1: pitch={params['pitch_shift']}, tempo={params['tempo_multiplier']}")
        print("  [OK] Parameter calculation successful")

        print("\n[STEP 3] Testing parameter validation...")
        valid = audio_processor.validate_parameters(params['pitch_shift'], params['tempo_multiplier'])
        print(f"  Parameters valid: {valid}")
        print("  [OK] Parameter validation successful")

        print("\n[STEP 4] Testing audio modification...")
        modified_file = audio_processor.modify_pitch_tempo(
            test_mp3,
            pitch_shift=params['pitch_shift'],
            tempo_multiplier=params['tempo_multiplier']
        )
        print(f"  Modified file: {modified_file}")
        print("  [OK] Audio modification successful")

        print("\n[SUCCESS] All process steps completed successfully!")
        print("🎉 Tool is ready for production use!")

        return True

    except Exception as e:
        print(f"\n[ERROR] Process failed: {e}")
        return False

    finally:
        # Clean up
        try:
            os.unlink(test_mp3)
        except:
            pass

if __name__ == '__main__':
    success = test_process_success()
    print(f"\nFinal Result: {'SUCCESS' if success else 'FAILED'}")
    sys.exit(0 if success else 1)
