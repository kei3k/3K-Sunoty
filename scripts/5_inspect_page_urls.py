
import re
import os

def find_mp3_urls():
    source_file = "debug_page_source.html"
    if not os.path.exists(source_file):
        print(f"File {source_file} not found.")
        return

    with open(source_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Regex for Suno CDN URLs
    # Pattern: https://cdn1.suno.ai/INVALID_UUID.mp3 or similar
    # Typically: https://cdn1.suno.ai/[uuid].mp3
    
    # Try generic URL pattern first
    # patterns = [
    #     r'https://cdn1\.suno\.ai/[a-zA-Z0-9-]+\.mp3',
    #     r'https://cdn1\.suno\.ai/[a-zA-Z0-9-]+\.m3u8' # video playlist
    # ]
    
    # Broad search for any mp3
    mp3_matches = re.findall(r'(https?://[^\s"\']+\.mp3)', content)
    
    print(f"Found {len(mp3_matches)} MP3 URLs:")
    for url in list(set(mp3_matches))[:10]: # Show top 10 unique
        print(f"  - {url}")

    # Search for video/playlist
    m3u8_matches = re.findall(r'(https?://[^\s"\']+\.m3u8)', content)
    print(f"\nFound {len(m3u8_matches)} .m3u8 (HLS Video) URLs:")
    for url in list(set(m3u8_matches))[:10]:
        print(f"  - {url}")

if __name__ == "__main__":
    find_mp3_urls()
