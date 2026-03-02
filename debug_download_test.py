
import logging
import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver import ActionChains

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def debug_download_logic():
    user_data_dir = os.path.join(os.getcwd(), "chrome_profile")
    output_dir = os.path.join(os.getcwd(), "output", "music")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    print(f"Output Directory: {output_dir}")

    # Setup Chrome with Download Prefs
    options = webdriver.ChromeOptions()
    options.add_argument(f"user-data-dir={user_data_dir}")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    prefs = {
        "download.default_directory": os.path.abspath(output_dir),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    options.add_experimental_option("prefs", prefs)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_window_size(1920, 1080)
    
    try:
        logger.info("Navigating to Suno Create page...")
        driver.get("https://suno.com/create")
        time.sleep(5)
        
        print("\n" + "="*60)
        print("DEBUG SESSION: MULTI-SONG DOWNLOAD")
        print("="*60)
        print("Please manually log in if needed. Waiting 10s...")
        time.sleep(10)
        
        # 1. Find Rows
        print("\n[TEST] Looking for Song Rows...")
        rows = driver.find_elements(By.XPATH, "//div[@data-testid='clip-row']")
        print(f"Found {len(rows)} song rows.")
        
        if len(rows) < 2:
            print("❌ Warning: Less than 2 songs found. Cannot test dual download fully.")
        
        # Test downloading first 2 songs
        songs_to_test = rows[:2]
        
        import traceback
        
        def wait_for_new_file(extension, timeout=120):
            """Waits for a new file with extension to appear in output_dir"""
            print(f"      ⏳ Waiting max {timeout}s for {extension} file to appear...")
            start_time = time.time()
            initial_files = set(os.listdir(output_dir))
            
            while time.time() - start_time < timeout:
                current_files = set(os.listdir(output_dir))
                new_files = current_files - initial_files
                
                # Check if any new file matches extension and is not a partial download
                for f in new_files:
                    if f.endswith(extension) and not f.endswith(".crdownload") and not f.endswith(".tmp"):
                        print(f"      ✅ New file detected: {f}")
                        return True
                
                time.sleep(1)
            
            print(f"      ❌ Timeout waiting for {extension} file!")
            return False

        # Test downloading first 2 songs
        num_songs = min(2, len(rows))

        for i in range(num_songs):
            print(f"\n" + "="*40)
            print(f"--- Processing Song {i+1} ---")
            print("="*40)
            
            try:
                # 1. Re-find row
                current_rows = driver.find_elements(By.XPATH, "//div[@data-testid='clip-row']")
                if i >= len(current_rows):
                    print(f"❌ Error: Row index {i} out of range (DOM changed?)")
                    continue
                
                row = current_rows[i]
                
                # 2. Scroll & Highlight
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", row)
                time.sleep(1) 
                
                try:
                    print("   [1] Downloading Audio + Video (from same menu)...")
                    
                    # Right Click
                    actions = ActionChains(driver)
                    actions.context_click(row).perform()
                    time.sleep(1.0)
                    
                    # Find "Download" and click
                    download_menu = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Download')]"))
                    )
                    print(f"      Found 'Download': {download_menu.text}")
                    download_menu.click()
                    time.sleep(1.0)
                    
                    # DEBUG: Print ALL visible elements that look like menu items
                    print("      [DEBUG] Looking for all submenu options...")
                    all_elements = driver.find_elements(By.XPATH, "//div[@role='menuitem'] | //span[contains(@class, 'chakra')] | //*[contains(text(), 'Audio')] | //*[contains(text(), 'Video')] | //*[contains(text(), 'MP')]")
                    print(f"      [DEBUG] Found {len(all_elements)} potential menu elements:")
                    for el in all_elements[:10]:  # Limit to first 10
                        try:
                            if el.is_displayed() and el.text.strip():
                                print(f"         - Tag:{el.tag_name}, Text:'{el.text}', Display:{el.is_displayed()}")
                        except:
                            pass
                    
                    # STRATEGY: Find BOTH elements first, then click both quickly
                    audio_opt = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'MP3 Audio')]"))
                    )
                    video_opt = driver.find_element(By.XPATH, "//span[contains(text(), 'Video')]")
                    
                    print(f"      Found Audio: '{audio_opt.text}'")
                    print(f"      Found Video: '{video_opt.text}'")
                    
                    # Click Audio first
                    audio_opt.click()
                    print("      ✅ Clicked Audio.")
                    time.sleep(0.3)
                    
                    # Immediately click Video (before menu closes)
                    try:
                        video_opt.click()
                        print("      ✅ Clicked Video.")
                    except:
                        print("      ⚠️ Video click failed (menu closed). Reopening...")
                        # Re-open menu
                        try: driver.find_element(By.TAG_NAME, "body").click()
                        except: pass
                        time.sleep(0.5)
                        actions.context_click(row).perform()
                        time.sleep(1.0)
                        download_menu = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Download')]"))
                        )
                        download_menu.click()
                        time.sleep(1.0)
                        video_opt = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Video')]"))
                        )
                        video_opt.click()
                        print("      ✅ Clicked Video (on retry).")
                    
                    # CHECK FOR TOAST
                    try:
                        toast_xpath = '//*[@id="chakra-toast-manager-bottom"]/div/div/div/div[1]/h3'
                        toast = WebDriverWait(driver, 5).until(
                            EC.visibility_of_element_located((By.XPATH, toast_xpath))
                        )
                        print(f"      ✅ Toast Detected: '{toast.text}'")
                    except:
                        pass
                    
                    # SMART WAIT FOR MP3 (10s - fast download)
                    wait_for_new_file(".mp3", timeout=10)
                    
                    # SMART WAIT FOR VIDEO (30s - or skip if too slow)
                    wait_for_new_file(".mp4", timeout=30)
                    
                    # Reset
                    try: driver.find_element(By.TAG_NAME, "body").click()
                    except: pass
                    
                except Exception as e:
                    print(f"   ❌ Download Failed: {e}")
                    traceback.print_exc()

                # Remove highlight
                try: driver.execute_script("arguments[0].style.border=''", row)
                except: pass
            
            except Exception as outer_e:
                print(f"❌ Error processing Row {i}: {outer_e}")

            time.sleep(2)

        print("\n[VERIFICATION] Checking Output Folder...")
        files = os.listdir(output_dir)
        print(f"Files in {output_dir}:")
        for f in files:
            print(f" - {f}")

        if len(files) > 0:
            print("✅ SUCCESS: Files detected!")
        else:
            print("❌ FAILURE: No files found in output directory.")

    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        print("\nClosing browser in 60 seconds (or press Ctrl+C)...")
        time.sleep(60)
        driver.quit()

if __name__ == "__main__":
    debug_download_logic()
