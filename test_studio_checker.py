"""
Test script for YouTube Studio Selenium checker.

Run this with a known video ID that has copyright claims to verify detection works.
"""

import os
import sys

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))

from scripts.modules.youtube_studio_checker import YouTubeStudioChecker

def test_check_by_video_id():
    """Test checking copyright by video ID."""
    
    # Replace with actual video ID that has copyright claims
    test_video_id = input("Enter video ID to test (or press Enter for default): ").strip()
    if not test_video_id:
        test_video_id = "PKbaswAtCkE"  # Example ID from recent uploads
    
    print(f"\n[TEST] Checking video: {test_video_id}")
    print("=" * 50)
    
    checker = YouTubeStudioChecker(
        user_data_dir=os.path.join(os.getcwd(), "chrome_profile"),
        headless=False  # Show browser for debugging
    )
    
    try:
        result = checker.check_copyright_by_video_id(test_video_id)
        
        print("\n[RESULT]")
        print(f"  Status: {result.get('status')}")
        print(f"  Has Copyright: {result.get('has_copyright')}")
        print(f"  Claim Type: {result.get('claim_type')}")
        print(f"  Claims: {result.get('claims')}")
        
        if result.get('has_copyright'):
            print("\n✅ SUCCESS: Copyright detection working correctly!")
        else:
            print("\n⚠️ No copyright detected - verify this is expected!")
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        
    finally:
        input("\nPress Enter to close browser...")
        checker.close()


if __name__ == "__main__":
    test_check_by_video_id()
