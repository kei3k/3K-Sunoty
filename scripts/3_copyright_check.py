#!/usr/bin/env python3
"""
Standalone YouTube Copyright Checker.

Checks if an audio or video file has copyright claims on YouTube
by uploading it as an unlisted video and polling the status.
"""

import os
import sys
import io
import json
import argparse
from pathlib import Path
from datetime import datetime

# Fix encoding for Vietnamese characters on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add scripts directory to path for imports
scripts_dir = Path(__file__).parent
root_dir = scripts_dir.parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

try:
    from modules.youtube_copyright_checker import youtube_checker
    from modules.video_converter import video_converter
    from utils.logger import logger
    from utils.config_loader import config
except ImportError:
    # Fallback for direct execution if paths are weird
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from modules.youtube_copyright_checker import youtube_checker
    from modules.video_converter import video_converter
    from utils.logger import logger
    from utils.config_loader import config

def run_action(mode: str, input_path: str, channel_id: str, video_id: str = None, keep_video: bool = False, profile_name: str = 'default') -> dict:
    """Execute logical action based on mode."""
    
    # Switch profile if needed
    if profile_name and profile_name != 'default':
        try:
            youtube_checker.switch_profile(profile_name)
        except Exception as e:
            return {"status": "error", "message": f"Failed to switch profile: {e}"}
            
    # Setup Channel ID
    if channel_id:
        os.environ["YOUTUBE_CHANNEL_ID"] = channel_id

    # --- UPLOAD MODE ---
    if mode == 'upload' or mode == 'full':
        input_path = os.path.abspath(input_path)
        if not os.path.exists(input_path):
            return {"status": "error", "message": f"File not found: {input_path}"}
            
        ext = os.path.splitext(input_path)[1].lower()
        is_video = ext in ['.mp4', '.avi', '.mkv', '.mov', '.webm']
        is_audio = ext in ['.mp3', '.wav', '.aac', '.flac', '.m4a']
        video_path = input_path
        temp_files_to_cleanup = []
        
        try:
            if is_audio:
                # Audio needs conversion to video for YouTube upload
                print("[INFO] Input is audio. Converting to temporary video...")
                try:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    video_path = os.path.join(os.path.dirname(input_path), f"temp_check_{timestamp}.mp4")
                    conversion_result = video_converter.convert_for_youtube(
                        audio_file=input_path, output_video=video_path, visualization='simple'
                    )
                    if conversion_result.get('status') != 'success':
                        raise Exception(f"Video conversion failed: {conversion_result.get('error')}")
                    temp_files_to_cleanup.append(video_path)
                except Exception as conv_err:
                    return {"status": "error", "message": f"Audio→Video conversion failed: {conv_err}. Try using an MP4 file instead."}
            elif is_video:
                print(f"[INFO] Input is video ({ext}), uploading directly...")
            else:
                return {"status": "error", "message": f"Unsupported file type: {ext}. Use MP4 or MP3."}
            
            song_name = os.path.splitext(os.path.basename(input_path))[0]
            title = song_name[:95] if len(song_name) > 95 else song_name
            
            print(f"[INFO] Uploading '{title}' (Account: {profile_name})...")
            print(f"[INFO] File: {video_path}")
            
            upload_result = youtube_checker.upload_test_video(
                audio_file=input_path if is_audio else None,
                video_file=video_path,
                title=title,
                privacy='unlisted'
            )
            video_id = upload_result['id']
            print(f"[SUCCESS] Uploaded. Video ID: {video_id}")
            
            if mode == 'upload':
                return {'status': 'success', 'video_id': video_id, 'song_name': song_name}
                
        except Exception as e:
            print(f"[ERROR] Upload failed: {e}")
            return {"status": "error", "message": str(e)}
        finally:
            if temp_files_to_cleanup:
                for f in temp_files_to_cleanup: 
                    try: os.remove(f) 
                    except: pass

    # --- CHECK MODE (Selenium YouTube Studio) ---
    if mode == 'check' or mode == 'full':
        if not video_id:
            return {"status": "error", "message": "Video ID required for check mode"}
            
        try:
            print(f"[INFO] Checking copyright via YouTube Studio for {video_id}...")
            
            # Wait for processing via API first (faster than Selenium polling)
            print(f"[INFO] Waiting for YouTube to finish processing...")
            api_status = youtube_checker.poll_copyright_status(video_id, max_wait_time=180)
            
            if api_status.get('timeout'):
                print(f"[WARNING] Processing timeout - will still try Selenium check")
            else:
                print(f"[INFO] Video processed. Now checking copyright via Studio...")
            
            # Use Selenium to get accurate copyright info
            try:
                from modules.youtube_studio_checker import studio_checker
                
                studio_result = studio_checker.check_copyright_by_video_id(video_id)
                
                has_copyright = studio_result.get('has_copyright', False)
                claim_type = studio_result.get('claim_type')
                claims = studio_result.get('claims', [])
                
                # Close browser to free resources
                studio_checker.close()
                
            except Exception as selenium_err:
                print(f"[WARNING] Selenium check failed: {selenium_err}")
                print(f"[INFO] Falling back to API result...")
                # Fallback to API result
                has_copyright = api_status.get('has_copyright', False)
                claim_type = api_status.get('claim_type')
                claims = api_status.get('claims', [])
            
            # Print detailed result for log parsing
            if has_copyright:
                if claim_type == 'blocked':
                    print(f"[CRITICAL] ❌ VIDEO BLOCKED - {video_id}")
                elif claim_type == 'claimed':
                    print(f"[WARNING] ⚠️ CONTENT ID CLAIM - {video_id}")
                else:
                    print(f"[ALERT] Copyright Detected for {video_id}")
                    
                # Print claims details
                for i, claim in enumerate(claims, 1):
                    print(f"  Claim {i}: {claim.get('reason', 'Unknown reason')}")
                    
            else:
                print(f"[SUCCESS] ✅ No Claims for {video_id}")

            # Auto delete logic
            auto_delete = config.get_test_upload_settings().get('auto_delete_after_check', True)
            if keep_video:
                auto_delete = False
                
            if auto_delete:
                try:
                    print(f"[INFO] Deleting video {video_id}...")
                    youtube_checker.delete_video(video_id)
                except Exception as del_err:
                    print(f"[WARNING] Could not delete video: {del_err}")
                    print(f"[INFO] Please delete manually: https://studio.youtube.com/video/{video_id}/edit")
                
            return {
                'status': 'success', 
                'video_id': video_id, 
                'has_copyright': has_copyright,
                'claim_type': claim_type,
                'claims': claims,
                'deleted': auto_delete
            }

            
        except Exception as e:
            return {"status": "error", "message": f"Check failed: {str(e)}"}

    # --- SCAN MODE (Check Recent Videos) ---
    if mode == 'scan':
        try:
            print(f"[INFO] Scanning recent videos for copyright status...")
            from modules.youtube_studio_checker import studio_checker
            
            results = studio_checker.check_recent_videos(limit=20)
            
            print(f"[INFO] Scan complete. Closing browser in 10s...", flush=True)
            import time
            time.sleep(10)
            
            studio_checker.close()
            
            print(f"\n[SCAN RESULTS] Found {len(results)} videos.", flush=True)
            
            # Print using ASCII-safe format (avoid Vietnamese chars causing encoding errors)
            print("[DEBUG] Starting result loop...", flush=True)
            for idx, res in enumerate(results):
                # Use sanitized title (ASCII only) or fallback to index
                raw_title = res.get('video_title', 'Unknown')
                # Remove non-ASCII chars
                safe_title = ''.join(c if ord(c) < 128 else '?' for c in raw_title)
                if len(safe_title) > 50:
                    safe_title = safe_title[:47] + "..."
                
                status = "CLEAN" if not res['has_copyright'] else "COPYRIGHT"
                
                if res['has_copyright']:
                    print(f"[ALERT] {status}: [{idx+1}] {safe_title}", flush=True)
                else:
                    print(f"[SUCCESS] {status}: [{idx+1}] {safe_title}", flush=True)
            
            print("[DEBUG] Finished result loop.", flush=True)
            
            return {'status': 'success', 'scanned': len(results), 'details': results}
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"status": "error", "message": f"Scan failed: {str(e)}"}

    return {"status": "error", "message": "Invalid mode"}

def main():
    parser = argparse.ArgumentParser(description='Standalone Copyright Checker')
    parser.add_argument('input_path', nargs='?', help='Path to audio or video file')
    parser.add_argument('--channel-id', help='YouTube Channel ID', default='')
    parser.add_argument('--keep-video', action='store_true', help='Do not delete video after check')
    parser.add_argument('--mode', choices=['full', 'upload', 'check', 'scan'], default='full', help='Action mode')
    parser.add_argument('--video-id', help='Video ID for check mode')
    parser.add_argument('--profile', default='default', help='API Account Profile')
    
    args = parser.parse_args()
    
    print(f"[DEBUG] args.profile = {args.profile}")
    
    result = run_action(args.mode, args.input_path, args.channel_id, args.video_id, args.keep_video, args.profile)
    print(json.dumps(result, indent=2))
    return 0 if result['status'] == 'success' else 1


if __name__ == "__main__":
    exit(main())
