
import logging
import os
import time
from selenium_suno import SunoBrowserAutomation
from selenium.webdriver.common.by import By

# Setup logging to file
if os.path.exists("debug_suno.log"):
    os.remove("debug_suno.log")
    
logging.basicConfig(
    filename="debug_suno.log",
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_suno_interaction():
    logger.info("Starting Debug Session")
    
    # Use the same profile path as app.py
    user_data_dir = os.path.join(os.getcwd(), "chrome_profile")
    logger.info(f"User Data Dir: {user_data_dir}")
    
    automation = SunoBrowserAutomation(headless=False, user_data_dir=user_data_dir)
    
    try:
        logger.info("Navigating to https://suno.com/create")
        automation.driver.get("https://suno.com/create")
        time.sleep(5)
        
        logger.info("Checking for 'Create' button...")
        buttons = automation.driver.find_elements(By.XPATH, "//button")
        logger.info(f"Found {len(buttons)} buttons")
        
        create_btns = [b.text for b in buttons if 'Create' in b.text]
        logger.info(f"Buttons with 'Create': {create_btns}")

        logger.info("Checking for file input...")
        inputs = automation.driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
        logger.info(f"Found {len(inputs)} file inputs")
        
        if inputs:
            logger.info("Attempting to upload dummy file...")
            # Create dummy file
            dummy_path = os.path.abspath("test_audio.mp3")
            with open(dummy_path, "w") as f:
                f.write("dummy content")
                
            inputs[0].send_keys(dummy_path)
            logger.info("Send keys executed.")
            time.sleep(2)
        else:
            logger.error("No file input found! Page source dump:")
            logger.error(automation.driver.page_source[:2000]) # First 2000 chars

    except Exception as e:
        logger.error(f"Error during debug: {e}", exc_info=True)
        
    finally:
        logger.info("Closing browser")
        automation.close()

if __name__ == "__main__":
    test_suno_interaction()
