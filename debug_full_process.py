
"""
Debug script for FULL PROCESS: Upload -> Rename -> Save -> Select Cover -> Create
Based on user feedback that previous debug steps were working.
"""
import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

def debug_full_process():
    # Setup Driver
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    
    # Use saved profile - MUST MATCH app.py (chrome_profile)
    user_data_dir = os.path.join(os.getcwd(), "chrome_profile")
    options.add_argument(f"user-data-dir={user_data_dir}")
    print(f"Using Profile: {user_data_dir}")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        print("\n" + "="*60)
        print("DEBUG: FULL PROCESS TEST (UNTIL SUCCESS)")
        print("="*60)
        driver.get("https://suno.com/create")
        
        # 1. UPLOAD
        print("\n--- [STEP 1] UPLOAD ---")
        print("👉 Attempting to find file input and upload 'test_audio.mp3'...")
        audio_path = os.path.abspath("test_audio.mp3")
        if not os.path.exists(audio_path):
            with open(audio_path, "wb") as f: f.write(b"ID3" + b'\x00'*10)
            
        try:
             # Try standard finding for input
             file_input = driver.find_element(By.CSS_SELECTOR, "input[type='file']")
             file_input.send_keys(audio_path)
             print("✅ File sent to input. Waiting for prompt/modal...")
             time.sleep(5)
        except Exception as e:
             print(f"⚠️ Auto-upload failed ({e}). PLEASE MANUALLY UPLOAD A FILE NOW.")
             time.sleep(15)

        # 2. AGREE
        print("\n--- [STEP 2] AGREE TO TERMS ---")
        try:
            xpath = "//*[contains(text(), 'Agree to Terms') or contains(text(), 'I Agree')]"
            btn = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, xpath)))
            driver.execute_script("arguments[0].click();", btn)
            print("✅ Clicked Agree.")
            time.sleep(1)
        except:
            print("ℹ️ Agree button not found (skipped).")

        # 3. RENAME
        print("\n--- [STEP 3] RENAME ---")
        try:
            # User's XPath for Edit Button (Proven working in previous debug)
            print("Looking for Edit Button (Full XPath)...")
            edit_btn_xpath = "/html/body/div[9]/div[3]/div/section/div/div[2]/div[1]/div/button"
            
            # Fallback path if index changes slightly?
            # edit_btn_xpath = "//h2/following-sibling::div//button" 
            
            edit_btn = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, edit_btn_xpath)))
            print("✅ Found Edit Button.")
            driver.execute_script("arguments[0].click();", edit_btn)
            time.sleep(2)
            
            # Type Name
            active = driver.switch_to.active_element
            print(f"Active element tag: {active.tag_name}")
            active.send_keys(Keys.CONTROL + "a")
            active.send_keys(Keys.BACKSPACE)
            active.send_keys("DEBUG SUCCESS SONG")
            active.send_keys(Keys.RETURN)
            print("✅ Renamed and pressed Enter.")
            time.sleep(2)
            
        except Exception as e:
            print(f"⚠️ Rename failed: {e}")

        # 4. SAVE
        print("\n--- [STEP 4] SAVE ---")
        try:
             save_btn = driver.find_element(By.XPATH, "//button[contains(., 'Save')]")
             driver.execute_script("arguments[0].click();", save_btn)
             print("✅ Clicked Save.")
             time.sleep(3) # Wait for modal close
        except:
             print("⚠️ Save button not found (maybe Enter key saved it?).")

        # 5. SELECT COVER
        print("\n--- [STEP 5] SELECT COVER ---")
        try:
             # User-Provided XPath
             cover_xpath = "/html/body/div[9]/div[3]/div/section/div/div/div[1]/div[3]/button[1]"
             print(f"Looking for Cover Button: {cover_xpath}")
             
             cover_btn = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, cover_xpath)))
             driver.execute_script("arguments[0].style.border='3px solid purple'", cover_btn)
             driver.execute_script("arguments[0].click();", cover_btn)
             print("✅ Clicked Cover.")
             time.sleep(2)
        except Exception as e:
             print(f"⚠️ Cover selection error: {e}")

        # 5.5 CONTINUE
        print("\n--- [STEP 5.5] CONTINUE ---")
        try:
             continue_xpath = "/html/body/div[9]/div[3]/div/section/div/div/div[2]/button/span"
             print(f"Looking for Continue Button: {continue_xpath}")
             cont_btn = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, continue_xpath)))
             driver.execute_script("arguments[0].style.border='3px solid orange'", cont_btn)
             driver.execute_script("arguments[0].click();", cont_btn)
             print("✅ Clicked Continue.")
             time.sleep(2)
        except Exception as e:
             print(f"⚠️ Continue button error: {e}")

        # 6. WAIT FOR UPLOAD & CREATE
        print("\n--- [STEP 6] WAIT FOR READY SIGNAL (Cover) & CREATE ---")
        try:
             # User provided XPath for the cover element that appears when upload is ready
             ready_cover_xpath = "/html/body/div[1]/div[1]/div[2]/div[1]/div/div/div/div/div/div/div/div[3]/div/div[2]/div[3]/div[1]/div[2]/div[1]/div[1]/div[2]/button/span"
             print(f"Waiting for Cover to appear (Signal for Ready): {ready_cover_xpath}")
             WebDriverWait(driver, 60).until(EC.visibility_of_element_located((By.XPATH, ready_cover_xpath)))
             print("✅ CAUGHT SIGNAL: Cover appeared! Process ready.")
             time.sleep(2)
        except Exception as e:
             print(f"⚠️ Timed out waiting for cover signal: {e}")
        
        try:
             # Look for Create button
             create_btn = driver.find_element(By.XPATH, "//button[contains(., 'Create')]")
             driver.execute_script("arguments[0].scrollIntoView(true);", create_btn)
             time.sleep(1)
             # highlight
             driver.execute_script("arguments[0].style.backgroundColor='yellow'", create_btn)
             
             print("Please watch browser... Will click Create in 3s...")
             time.sleep(3)
             driver.execute_script("arguments[0].click();", create_btn)
             print("✅ Clicked Create.")
             
        except Exception as e:
             print(f"⚠️ Create button error: {e}")

        print("\n" + "="*60)
        print("WAITING FOR SUCCESS... (Monitor Browser)")
        print("="*60)
        
        while True:
            time.sleep(1)
            
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_full_process()
