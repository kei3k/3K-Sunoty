"""
YouTube OAuth 2.0 Handler.
Handles authentication and token management for YouTube Data API.
"""

import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Scopes required for Upload and Delete
SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube.readonly',
    'https://www.googleapis.com/auth/youtube.force-ssl' # Needed for delete
]

def get_credential_paths(profile_name='default'):
    """Get paths for secret and token files based on profile."""
    base_dir = os.getcwd()
    creds_dir = os.path.join(base_dir, 'credentials')
    
    if not os.path.exists(creds_dir):
        os.makedirs(creds_dir, exist_ok=True)
        
    if profile_name == 'default':
        return 'client_secrets.json', 'token.pickle'
    else:
        # Sanitize profile name
        safe_name = "".join([c for c in profile_name if c.isalnum() or c in (' ', '_', '-')]).strip()
        secret_file = os.path.join(creds_dir, f"{safe_name}.json")
        token_file = os.path.join(base_dir, f".token_{safe_name}.pickle") # Keep tokens in root or hidden
        return secret_file, token_file

def list_available_profiles():
    """List all available API profiles (default + json files in credentials/)."""
    profiles = []
    
    # Check default
    if os.path.exists('client_secrets.json'):
        profiles.append('default')
        
    # Check credentials folder
    creds_dir = os.path.join(os.getcwd(), 'credentials')
    if os.path.exists(creds_dir):
        for f in os.listdir(creds_dir):
            if f.endswith('.json'):
                profiles.append(os.path.splitext(f)[0])
                
    return sorted(list(set(profiles)))

def get_authenticated_service(profile_name='default'):
    """
    Get authenticated YouTube service for specific profile.
    
    Args:
        profile_name (str): Name of the profile (json filename in credentials/)
    
    Returns:
        googleapiclient.discovery.Resource: Authenticated YouTube service
    """
    creds = None
    client_secrets_file, token_file = get_credential_paths(profile_name)
    print(f"[DEBUG_AUTH] Profile: {profile_name}")
    print(f"[DEBUG_AUTH] Secrets: {client_secrets_file}")
    print(f"[DEBUG_AUTH] Token: {token_file}")
    
    # Load existing token if available
    if os.path.exists(token_file):
        try:
            with open(token_file, 'rb') as token:
                creds = pickle.load(token)
            print("[DEBUG_AUTH] Loaded existing token.")
        except Exception as e:
            print(f"Warning: Corrupt token file {token_file}: {e}")
            creds = None
            
    # If no valid credentials available, let user log in.
    if not creds or not creds.valid:
        print("[DEBUG_AUTH] Credentials invalid or expired.")
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                print("[DEBUG_AUTH] Token refreshed.")
            except Exception as e:
                print(f"[DEBUG_AUTH] Refresh failed: {e}")
                # Refresh failed, need full login
                creds = None
                
        if not creds:
            if not os.path.exists(client_secrets_file):
                raise FileNotFoundError(f"Missing {client_secrets_file} for profile '{profile_name}'. Please add json file to credentials/ folder.")
            
            print("[DEBUG_AUTH] Starting Local Server Flow (Browser should open)...")    
            flow = InstalledAppFlow.from_client_secrets_file(
                client_secrets_file, SCOPES)
            creds = flow.run_local_server(port=0)
            
        # Save the credentials for the next run
        with open(token_file, 'wb') as token:
            pickle.dump(creds, token)
            print(f"[DEBUG_AUTH] Token saved to {token_file}")

    return build('youtube', 'v3', credentials=creds)


if __name__ == "__main__":
    try:
        service = get_authenticated_service()
        print("Successfully authenticated with YouTube API!")
    except Exception as e:
        print(f"Authentication failed: {e}")
