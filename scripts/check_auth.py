import sys
import os
from pathlib import Path

# Add scripts directory to path for imports
scripts_dir = Path(__file__).parent
root_dir = scripts_dir.parent
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from modules.youtube_auth import get_authenticated_service, list_available_profiles

def main():
    print("=== API Profile Authentication Helper ===")
    profiles = list_available_profiles()
    
    if not profiles:
        print("No profiles found.")
        return

    print("Available Profiles:")
    for i, p in enumerate(profiles):
        print(f"{i + 1}. {p}")
        
    choice = input("\nSelect profile to authenticate (number): ")
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(profiles):
            profile_name = profiles[idx]
            print(f"\nAuthenticating '{profile_name}'...")
            print("Please check your browser to login if prompted...")
            
            service = get_authenticated_service(profile_name)
            
            # Test a call
            channels_response = service.channels().list(
                mine=True,
                part='snippet'
            ).execute()
            
            title = channels_response['items'][0]['snippet']['title']
            print(f"\n✅ SUCCESS! Authenticated as channel: {title}")
        else:
            print("Invalid selection")
    except ValueError:
        print("Invalid input")
    except Exception as e:
        print(f"\n❌ FAILED: {e}")

    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
