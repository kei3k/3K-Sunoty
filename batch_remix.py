#!/usr/bin/env python3
"""
Batch Remix Script for YouTube Automation Pipeline

This script is called by 3K-yt-trending to:
1. Read songs_to_generate.json (exported from trending tool)
2. Remix each song with Suno using the specified style
3. Download remixed songs (Download Only mode)
4. Run batch copyright check
5. Report results back

Usage:
  python batch_remix.py                     # Process all songs in queue
  python batch_remix.py --download-only --count 3     # Only download, skip remix
  python batch_remix.py --copyright-check   # Only run copyright check
"""

import os
import sys
import json
import time
import argparse
import logging
from datetime import datetime
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('batch_remix.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Paths
SUNOTY_PATH = Path(__file__).parent
SONGS_FILE = SUNOTY_PATH / "songs_to_generate.json"
OUTPUT_PATH = SUNOTY_PATH / "output" / "remix"
DOWNLOADS_PATH = SUNOTY_PATH / "downloads"
RESULTS_FILE = SUNOTY_PATH / "batch_results.json"

# Ensure directories exist
OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
DOWNLOADS_PATH.mkdir(parents=True, exist_ok=True)


def load_songs():
    """Load songs from queue file"""
    if not SONGS_FILE.exists():
        logger.warning(f"No songs file found: {SONGS_FILE}")
        return []
    
    try:
        with open(SONGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load songs: {e}")
        return []


def save_results(results):
    """Save processing results"""
    try:
        with open(RESULTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        logger.info(f"Results saved to: {RESULTS_FILE}")
    except Exception as e:
        logger.error(f"Failed to save results: {e}")


def run_remix_batch():
    """Run Suno remix for all songs in queue"""
    songs = load_songs()
    
    if not songs:
        logger.info("No songs to process")
        return []
    
    logger.info(f"=" * 60)
    logger.info(f"BATCH REMIX - {len(songs)} songs")
    logger.info(f"=" * 60)
    
    results = []
    
    try:
        from selenium_suno import SunoBrowserAutomation
        from batch_create import create_song_only
        
        # Initialize browser
        chrome_profile = SUNOTY_PATH / "chrome_profile"
        suno = SunoBrowserAutomation(
            headless=False, 
            user_data_dir=str(chrome_profile)
        )
        suno.navigate_to_suno()
        
        # Wait for login
        if not suno.wait_for_login(timeout=60):
            logger.error("Login timeout!")
            suno.close()
            return [{"error": "Login timeout"}]
        
        logger.info("Logged in to Suno")
        
        # Process each song
        for i, song in enumerate(songs, 1):
            logger.info(f"\n{'─' * 50}")
            logger.info(f"[{i}/{len(songs)}] {song.get('title', 'Unknown')}")
            logger.info(f"{'─' * 50}")
            
            result = {
                "title": song.get('title'),
                "original_video_id": song.get('original_video_id'),
                "target_channel_id": song.get('target_channel_id'),
                "style": song.get('style'),
                "status": "pending",
                "started_at": datetime.now().isoformat()
            }
            
            audio_path = song.get('audio_path')
            if not audio_path or not os.path.exists(audio_path):
                logger.error(f"Audio file not found: {audio_path}")
                result["status"] = "error"
                result["error"] = "Audio file not found"
                results.append(result)
                continue
            
            try:
                # Create song using batch_create module
                success = create_song_only(
                    suno,
                    audio_path=audio_path,
                    title=song.get('title', 'Untitled'),
                    prompt=song.get('prompt', 'Cover of uploaded song'),
                    log_callback=lambda msg: logger.info(msg.strip())
                )
                
                if success:
                    result["status"] = "submitted"
                    logger.info(f"✅ Song submitted: {song.get('title')}")
                else:
                    result["status"] = "failed"
                    result["error"] = "Create failed"
                    logger.error(f"❌ Failed: {song.get('title')}")
                
            except Exception as e:
                result["status"] = "error"
                result["error"] = str(e)
                logger.error(f"❌ Exception: {e}")
            
            result["finished_at"] = datetime.now().isoformat()
            results.append(result)
            
            # Wait between songs
            if i < len(songs):
                logger.info("Waiting 10s before next song...")
                time.sleep(10)
        
        suno.close()
        
    except ImportError as e:
        logger.error(f"Import error: {e}")
        return [{"error": f"Import error: {e}"}]
    except Exception as e:
        logger.error(f"Batch remix error: {e}")
        return [{"error": str(e)}]
    
    # Clear the queue after processing
    try:
        with open(SONGS_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)
        logger.info("Cleared songs queue")
    except:
        pass
    
    save_results(results)
    return results


def run_download_only(count=3):
    """Download completed songs from Suno library using robust batch_download"""
    logger.info("=" * 60)
    logger.info(f"📥 DOWNLOAD ONLY MODE (Count: {count})")
    logger.info("=" * 60)
    
    try:
        from selenium_suno import SunoBrowserAutomation
        
        chrome_profile = SUNOTY_PATH / "chrome_profile"
        # headless=False to allow user to see/login if needed
        suno = SunoBrowserAutomation(
            headless=False,
            user_data_dir=str(chrome_profile)
        )
        suno.navigate_to_suno()
        
        if not suno.wait_for_login(timeout=60):
            logger.error("Login timeout!")
            suno.close()
            return {"error": "Login timeout"}
        
        # Call the robust batch_download method from selenium_suno.py
        # num_songs is the number of input songs. Each input = 2 outputs.
        # User said count=3, assuming 3 inputs.
        downloaded_count = suno.batch_download(num_songs=count)
        
        suno.close()
        
        return {
            "status": "success",
            "downloaded": downloaded_count
        }
        
    except Exception as e:
        logger.error(f"Download error: {e}")
        return {"error": str(e)}


def run_copyright_check():
    """Run batch copyright check on recent uploads"""
    logger.info("=" * 60)
    logger.info("✅ BATCH COPYRIGHT CHECK")
    logger.info("=" * 60)
    
    try:
        # Add scripts path
        scripts_path = SUNOTY_PATH / "scripts"
        sys.path.insert(0, str(scripts_path))
        
        from modules.youtube_studio_checker import studio_checker
        
        # Scan recent videos
        results = studio_checker.check_recent_videos(limit=20)
        
        studio_checker.close()
        
        # Analyze results
        with_copyright = [r for r in results if r.get('has_copyright')]
        clean = [r for r in results if not r.get('has_copyright')]
        
        logger.info(f"\n{'=' * 50}")
        logger.info(f"📊 COPYRIGHT CHECK RESULTS")
        logger.info(f"{'=' * 50}")
        logger.info(f"Total scanned: {len(results)}")
        logger.info(f"✅ Clean: {len(clean)}")
        logger.info(f"⚠️ Copyright: {len(with_copyright)}")
        
        if with_copyright:
            logger.info(f"\n{'─' * 50}")
            logger.info("Videos with copyright claims:")
            for v in with_copyright:
                logger.info(f"  ❌ {v.get('video_title')}")
        
        return {
            "status": "success",
            "total": len(results),
            "clean": len(clean),
            "copyright": len(with_copyright),
            "copyright_videos": [v.get('video_title') for v in with_copyright],
            "details": results
        }
        
    except Exception as e:
        logger.error(f"Copyright check error: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


def main():
    parser = argparse.ArgumentParser(description='Batch Remix for YouTube Automation')
    parser.add_argument('--download-only', action='store_true', help='Only download, skip remix')
    parser.add_argument('--count', type=int, default=3, help='Number of songs to download')
    parser.add_argument('--copyright-check', action='store_true', help='Only run copyright check')
    parser.add_argument('--all', action='store_true', help='Run full pipeline: remix → download → copyright')
    
    args = parser.parse_args()
    
    results = {}
    
    if args.download_only:
        results = run_download_only(count=args.count)
    elif args.copyright_check:
        results = run_copyright_check()
    elif args.all:
        # Full pipeline
        logger.info("🚀 FULL PIPELINE MODE")
        
        # Step 1: Remix
        remix_results = run_remix_batch()
        results["remix"] = remix_results
        
        # Wait for Suno to process
        logger.info("\n⏳ Waiting 3 minutes for Suno to process...")
        time.sleep(180)
        
        # Step 2: Download
        download_results = run_download_only(count=args.count)
        results["download"] = download_results
        
        # Step 3: Copyright check (user needs to upload first)
        logger.info("\n⚠️ Upload videos to YouTube, then run:")
        logger.info("   python batch_remix.py --copyright-check")
        
    else:
        # Default: just remix
        results = run_remix_batch()
    
    # Print final results
    logger.info(f"\n{'=' * 60}")
    logger.info("📋 FINAL RESULTS")
    logger.info(f"{'=' * 60}")
    print(json.dumps(results, indent=2, ensure_ascii=False))
    
    if isinstance(results, dict) and results.get("error"):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
