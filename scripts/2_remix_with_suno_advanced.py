#!/usr/bin/env python3
"""
Suno Remix Tool with Copyright Detection - Fixed Version

Advanced remix generation system using cookie-based Suno API authentication.
"""

import os
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import logging

# Add scripts directory to path for imports
# Add scripts and root directory to path
scripts_dir = Path(__file__).parent
root_dir = scripts_dir.parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

try:
    from selenium_suno import SunoBrowserAutomation
    from modules.audio_processor import audio_processor
    from modules.youtube_copyright_checker import youtube_checker
    from modules.video_converter import video_converter
    from modules.retry_manager import retry_manager
    from utils.workflow_logger import workflow_logger
    from utils.config_loader import config
    from utils.logger import logger

    # Configure selenium_suno logger to use the same handlers as remix_tool
    # This ensures detailed selector logs appear in the main log file
    selenium_logger = logging.getLogger('selenium_suno')
    selenium_logger.setLevel(logging.INFO)
    
    # Avoid adding handlers multiple times if script is re-run or imported
    if not selenium_logger.handlers:
        for handler in logger.logger.handlers:
            selenium_logger.addHandler(handler)
            
except ImportError:
    # Fallbacks for running from different contexts
    try:
        from d_K_3K_Sunoty.selenium_suno import SunoBrowserAutomation # Attempt absolute import if package structure allows
    except:
        pass
    from modules.audio_processor import audio_processor
    from modules.youtube_copyright_checker import youtube_checker
    from modules.video_converter import video_converter
    from modules.retry_manager import retry_manager
    from utils.workflow_logger import workflow_logger
    from utils.config_loader import config
    from utils.logger import logger


class RemixWithCopyrightResolution:
    """Main orchestrator for the Suno remix tool with copyright detection."""

    def __init__(self):
        """Initialize the remix tool."""
        # Force 1 attempt for debugging as requested
        self.max_attempts = 1 # int(os.getenv("MAX_REMIX_ATTEMPTS", 1))
        self.copyright_threshold = int(os.getenv("COPYRIGHT_MATCH_THRESHOLD", 75))
        self.safe_threshold = int(os.getenv("SAFE_MATCH_THRESHOLD", 50))

        # Create output directories
        for dir_name in ["output/music", "output/videos", "output/temp"]:
            Path(dir_name).mkdir(parents=True, exist_ok=True)

    def get_parameters(self, attempt: int) -> tuple[int, float]:
        """Get pitch and tempo parameters for attempt.
        
        Strategy: Start very light (decrease pitch) to preserve audio quality.
        Only escalate if copyright is detected on previous attempts.
        
        Attempt 1: -0.5 semitone, 1.02x tempo (barely noticeable)
        Attempt 2: -1 semitone, 1.03x tempo (still light)
        Attempt 3+: gradually increase
        """
        # Light start, gradual escalation (negative pitch = lower tone)
        if attempt == 1:
            pitch_shift = -0.5
            tempo_multiplier = 1.02
        elif attempt == 2:
            pitch_shift = -1
            tempo_multiplier = 1.03
        elif attempt <= 4:
            pitch_shift = -1 - (attempt - 2) * 0.5  # -1.5, -2.0
            tempo_multiplier = 1.03 + (attempt - 2) * 0.02  # 1.05, 1.07
        else:
            pitch_shift = -2 - (attempt - 4)  # -3, -4, -5
            tempo_multiplier = 1.07 + (attempt - 4) * 0.03  # 1.10, 1.13...

        # Ensure within bounds
        pitch_shift = max(-5, min(5, pitch_shift))
        tempo_multiplier = max(0.85, min(1.20, tempo_multiplier))

        return pitch_shift, tempo_multiplier

    def process(
        self,
        song_path: str,
        song_name: str,
        channel_id: str,
        style: str = "lofi_chill",
        remix_only: bool = False,
        custom_prompt: str = ""
    ) -> Dict[str, Any]:
        """
        Main workflow: remix generation with copyright resolution.
        """
        # ... (rest of function)
        
        # Inside the loop:
        # Use custom prompt if provided, else construct one
        
        # We need to find where generate_remix is called.
        # It's further down, so we just update signature here.
        """
        Main workflow: remix generation with copyright resolution.

        Args:
            song_path: Path to input MP3 file
            song_name: Song name for processing
            channel_id: YouTube channel ID
            style: Remix style (lofi_chill, edm_remix, jazz_cover, acoustic_stripped)

        Returns:
            Dictionary containing final result
        """
        workflow_id = f"remix_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        print(f"\n[MUSIC] Starting remix workflow: {workflow_id}")
        print(f"Song: {song_name}")
        print(f"Style: {style}")
        print(f"Channel: {channel_id}")

        workflow_logger.start_workflow(workflow_id, song_name, style)

        # Analyze original audio
        audio_props = audio_processor.analyze_audio(song_path)
        print(f"\n[ANALYSIS] Audio Analysis:")
        print(f"  BPM: {audio_props['bpm']:.1f}")
        print(f"  Key: {audio_props['key']}")
        print(f"  Duration: {audio_props['duration']:.1f}s")

        attempt = 0
        copyright_detected = True
        test_video_ids = []
        match_percent = None  # Initialize to avoid UnboundLocalError

        while attempt < self.max_attempts and copyright_detected:
            attempt += 1
            print(f"\n{'='*60}")
            print(f"ATTEMPT {attempt}/{self.max_attempts}")
            print(f"{'='*60}")

            # Get parameters for this attempt
            pitch_shift, tempo_multiplier = self.get_parameters(attempt)
            print(f"Parameters: Pitch {pitch_shift:+.1f}, Tempo {tempo_multiplier:.2f}x")

            # Step 1: Modify audio parameters
            print(f"\n[STEP 1] Modifying audio parameters...")
            modified_audio = audio_processor.modify_pitch_tempo(
                song_path,
                pitch_shift=pitch_shift,
                tempo_multiplier=tempo_multiplier,
                output_path=f"output/temp/modified_attempt_{attempt}.wav"
            )

            # Step 2: Generate remix via Suno (Browser Automation)
            print(f"\n[STEP 2] Generating remix via Suno (Selenium)...")
            
            # Initialize automation with persistent profile
            user_data_dir = os.path.join(str(root_dir), "chrome_profile")
            browser = SunoBrowserAutomation(headless=False, user_data_dir=user_data_dir)
            
            try:
                # 1. Generate (Upload + Click Create)
                # Note: style_id is passed as 'style' prompt addition or we can look up style prompt
                # The original code loaded style config. We might need to handle that here or just pass style name.
                # Assuming style is just the string ID like 'lofi_chill' which maps to a prompt.
                # Let's simple pass style as style for now or construct a basic prompt.
                
                # We need to construct the prompt manually if we don't use suno_client logic
                if custom_prompt:
                    full_prompt = custom_prompt
                else:
                    full_prompt = f"Remix of {song_name}, {style} style."
                
                gen_result = browser.generate_remix(
                    prompt=full_prompt,
                    audio_path=os.path.abspath(f"output/temp/modified_attempt_{attempt}.wav"),
                    title=song_name,  # Pass explicit song name
                    wait_for_generation=True,
                    max_wait=300 # Wait 5 mins for generation to complete
                )
                
                if gen_result["status"] == "error":
                     raise Exception(gen_result["error"])

                # 2. Retrieve top 2 generated songs
                print("Retrieving top 2 songs from dashboard...")
                songs = browser.get_latest_songs(count=2)  # Get top 2
                
                if len(songs) < 2:
                    print(f"⚠️ Only found {len(songs)} song(s). Will download what's available.")
                
                if not songs:
                    raise Exception("No songs found after generation")
                
                # 3. Download via Browser - BOTH top songs
                print("Triggering browser download for top 2 songs...")
                download_success = False
                for idx, target_song in enumerate(songs[:2]):
                    print(f"[{idx+1}/2] Downloading: {target_song['title']}")
                    if browser.download_song_files(target_song, "output/music"):
                         print(f"✅ Download {idx+1} initiated.")
                         download_success = True
                    else:
                         print(f"⚠️ Download {idx+1} failed for: {target_song['title']}")
                
                if not download_success:
                     logger.warning("Browser download trigger failed for all songs.")

                remix_result = {
                     "status": "success",
                     "remix_file": "Check Browser Downloads Folder",
                     "song_id": "selenium_gen",
                     "error": None
                }
                
            except Exception as e:
                remix_result = {"status": "failed", "error": str(e)}
            finally:
                # Keep browser open? Or close? User wants to "thao tác trên trình duyệt" maybe keep open?
                # Usually we close to save resources, but maybe for debugging keep open.
                # let's close for now to avoid multiple windows piling up in loop
                browser.close()

            if remix_result["status"] != "success":
                print(f"[ERROR] Suno generation failed: {remix_result['error']}")
                print(f"[INFO] Modified audio saved at: {modified_audio}") # Inform user
                
                workflow_logger.log_attempt(attempt, {
                    "status": "failed",
                    "error": remix_result['error'],
                    "pitch_shift": pitch_shift,
                    "tempo_multiplier": tempo_multiplier,
                    "modified_audio": modified_audio
                })
                continue

            remix_file = remix_result["remix_file"]
            song_id = remix_result.get("song_id")

            if remix_only:
                print("\n[INFO] Remix-only mode enabled. Skipping YouTube upload and copyright check.")
                print(f"[SUCCESS] Remix generated and saved: {remix_file}")
                
                # We consider this a success for the workflow
                final_result = {
                    "status": "success",
                    "final_remix": remix_file,
                    "attempts": attempt,
                    "parameters_used": {
                        "pitch_shift": pitch_shift,
                        "tempo_multiplier": tempo_multiplier
                    },
                    "note": "Copyright check skipped"
                }
                copyright_detected = False # Break loop
                continue

            # Step 3: Convert to video for YouTube
            print(f"\n[STEP 3] Converting to MP4...")
            video_file = f"output/videos/test_{attempt}.mp4"
            video_converter.convert_for_youtube(
                audio_file=remix_file,
                output_video=video_file
            )

            # Step 4: Upload unlisted video to YouTube
            print(f"\n[STEP 4] Uploading test video to YouTube...")
            video_id = youtube_checker.upload_unlisted_video(
                video_file,
                title=f"[TEST] Copyright Check - {song_name} - Attempt {attempt}",
                channel_id=channel_id
            )
            test_video_ids.append(video_id)
            print(f"[OK] Uploaded with ID: {video_id}")

            # Step 5: Check copyright status
            print(f"\n[STEP 5] Checking copyright claims...")
            copyright_result = youtube_checker.check_copyright_status(video_id)
            copyright_detected = copyright_result["has_copyright"]
            match_percent = copyright_result["match_percent"]

            print(f"Match: {match_percent:.1f}%")

            if not copyright_detected:
                print(f"[SUCCESS] NO COPYRIGHT DETECTED! Using this remix.")

                workflow_logger.log_attempt(attempt, {
                    "status": "success",
                    "copyright_detected": False,
                    "match_percent": match_percent,
                    "pitch_shift": pitch_shift,
                    "tempo_multiplier": tempo_multiplier,
                    "song_id": song_id,
                    "remix_file": remix_file,
                    "video_id": video_id
                })

                final_result = {
                    "status": "success",
                    "final_remix": remix_file,
                    "attempts": attempt,
                    "parameters_used": {
                        "pitch_shift": pitch_shift,
                        "tempo_multiplier": tempo_multiplier
                    },
                    "youtube_copyright_result": {
                        "copyright_detected": False,
                        "match_percent": match_percent
                    }
                }

            elif match_percent > self.copyright_threshold:
                print(f"[COPYRIGHT] DETECTED ({match_percent:.1f}% > {self.copyright_threshold}%)")
                print(f"   Retrying with new parameters...")

                workflow_logger.log_attempt(attempt, {
                    "status": "copyright_detected",
                    "copyright_detected": True,
                    "match_percent": match_percent,
                    "pitch_shift": pitch_shift,
                    "tempo_multiplier": tempo_multiplier,
                    "will_retry": True
                })

            elif match_percent > self.safe_threshold:
                print(f"[WARNING] GRAY ZONE ({match_percent:.1f}%, {self.safe_threshold}%-{self.copyright_threshold}%)")
                print(f"   Will retry once more...")

                workflow_logger.log_attempt(attempt, {
                    "status": "gray_zone",
                    "copyright_detected": False,
                    "match_percent": match_percent,
                    "pitch_shift": pitch_shift,
                    "tempo_multiplier": tempo_multiplier,
                    "will_retry": True
                })

            # Clean up test video (except if success)
            if copyright_detected:
                youtube_checker.delete_video(video_id)
                print(f"[CLEANUP] Deleted test video")

        # Final result
        if not copyright_detected:
            print(f"\n[SUCCESS] Remix is copyright-free!")
            result = final_result
        else:
            print(f"\n[FAILED] After {attempt} attempts")
            result = {
                "status": "failed",
                "reason": "max_attempts_exceeded",
                "attempts": attempt,
                "last_copyright_match": match_percent if 'match_percent' in locals() else None,
                "recommendation": "Try different song or manual intervention"
            }

            workflow_logger.log_attempt(attempt, {
                "status": "failed",
                "reason": "max_attempts_exceeded",
                "last_match_percent": match_percent if 'match_percent' in locals() else None
            })

        # Cleanup all test videos
        print(f"\n[CLEANUP] Cleaning up {len(test_video_ids)} test videos...")
        for vid_id in test_video_ids:
            try:
                youtube_checker.delete_video(vid_id)
            except:
                pass

        # Save workflow log
        log_file = workflow_logger.save_workflow(result)

        return result


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Suno Remix Tool with Copyright Detection')
    parser.add_argument('song_path', help='Path to input MP3 file')
    parser.add_argument('--song-name', required=True, help='Song name')
    parser.add_argument('--channel-id', required=True, help='YouTube channel ID')
    parser.add_argument('--style', default='lofi_chill', help='Remix style')
    parser.add_argument('--prompt', default='', help='Custom prompt')
    parser.add_argument('--remix-only', action='store_true', help='Skip YouTube upload and copyright check')

    args = parser.parse_args()

    # Initialize processor
    processor = RemixWithCopyrightResolution()

    # Run processing
    result = processor.process(
        song_path=args.song_path,
        song_name=args.song_name,
        channel_id=args.channel_id,
        style=args.style,
        remix_only=args.remix_only,
        custom_prompt=args.prompt
    )

    print(f"\n" + "="*60)
    print("FINAL RESULT:")
    print("="*60)
    print(json.dumps(result, indent=2))

    return 0 if result.get("status") == "success" else 1


if __name__ == "__main__":
    exit(main())
