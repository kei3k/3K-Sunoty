
from selenium_suno import SunoBrowserAutomation
import os
import time

def run_debug_full():
    print("="*50)
    print("DEBUG: FULL GENERATION FLOW TEST")
    print("="*50)

    # 1. Initialize Driver
    # Use existing chrome profile
    user_data_dir = os.path.join(os.getcwd(), "chrome_profile")
    bot = SunoBrowserAutomation(headless=False, user_data_dir=user_data_dir)
    
    # 2. Prep Dummy Audio
    audio_path = os.path.abspath("test_audio.mp3")
    if not os.path.exists(audio_path):
        # Create 10s silent MP3 or simple WAV. 
        # Suno might reject invalid files, but let's try a simple file
        # Ideally copy a real file if available? 
        # Let's hope the user has 'test_audio.mp3' or we create a text file mimicking it
        with open(audio_path, "wb") as f:
             f.write(b'ID3' + b'\x00'*10) # Fake MP3 header
    
    # 3. Define Request
    # We call generate_remix directly
    prompt = "A test remix for debugging functionality"
    style = "acoustic"
    
    print(f"Start Remix Generation...")
    print(f"Audio: {audio_path}")
    print(f"Prompt: {prompt}")

    # 4. Run
    try:
        success = bot.generate_remix(
            prompt=prompt,
            audio_path=audio_path,
            style=style,
            wait_for_generation=True,
            max_wait=300 # 5 mins
        )
        
        if success:
            print("\n✅ SUCCESS: Song generation claimed successful by script.")
        else:
            print("\n❌ FAILED: Script reported failure.")

    except Exception as e:
        print(f"\n❌ EXCEPTION: {e}")
        import traceback
        traceback.print_exc()

    finally:
        print("\nPress Ctrl+C to exit browser...")
        while True:
            time.sleep(1)

if __name__ == "__main__":
    run_debug_full()
