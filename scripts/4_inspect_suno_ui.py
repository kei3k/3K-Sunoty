#!/usr/bin/env python3
"""
Suno UI Inspector Tool.

This script opens the Chrome browser with the EXACT profile used by the automation.
It allows you to manually navigate and inspect elements to find the correct valid selectors.

Instructions:
1. Run this script.
2. The browser will open. Ensure you are logged in.
3. Navigate to the page/state where the bot fails.
4. Right-click the element (button, input, etc.) you want the bot to interact with.
5. Select "Inspect" (Kiểm tra).
6. In the Elements panel, Right-click the highlighted HTML line -> Copy -> Copy XPath (or Copy selector).
7. Paste that XPath/Selector back to the AI assistant.
"""

import os
import sys
import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Add scripts directory to path for imports
scripts_dir = Path(__file__).parent
root_dir = scripts_dir.parent

def main():
    print("="*60)
    print("SUNO UI INSPECTOR MODE")
    print("="*60)
    print("[INFO] Opening Browser with persistent profile...")
    
    user_data_dir = os.path.join(str(root_dir), "chrome_profile")
    
    options = webdriver.ChromeOptions()
    options.add_argument(f"user-data-dir={user_data_dir}")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_window_size(1920, 1080)
    
    try:
        print("[INFO] Navigating to Suno.ai...")
        driver.get("https://suno.com/create")
        
        print("\n" + "="*60)
        print("INSTRUCTIONS FOR USER:")
        print("1. Please Login manually if asked.")
        print("2. Navigate to the screen where the bot gets stuck.")
        print("3. Mouse over the button/input triggering the issue.")
        print("4. Right Click -> Inspect (Kiểm tra).")
        print("5. Right Click highlighted code -> Copy -> Copy Full XPath.")
        print("6. Paste that XPath here in the chat.")
        print("="*60)
        
        while True:
            cmd = input("\n[COMMAND] Type 'test <xpath>' to verify a selector, or 'exit' to close: ")
            if cmd.lower() == 'exit':
                break
            
            if cmd.lower().startswith('test '):
                selector = cmd[5:].strip()
                try:
                    from selenium.webdriver.common.by import By
                    # Try XPath first
                    if selector.startswith("//") or selector.startswith("("):
                        elements = driver.find_elements(By.XPATH, selector)
                        print(f" -> Found {len(elements)} element(s) with XPath.")
                    else:
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        print(f" -> Found {len(elements)} element(s) with CSS Selector.")
                        
                    if elements:
                        # Highlight them
                        for i, el in enumerate(elements):
                            driver.execute_script("arguments[0].style.border='3px solid red'", el)
                            print(f"    Element {i+1}: Highlighted in RED.")
                    else:
                        print(" -> No elements found.")
                        
                except Exception as e:
                    print(f" -> Error testing selector: {e}")

    except Exception as e:
        print(f"[ERROR] Browser error: {e}")
    finally:
        print("[INFO] Closing browser...")
        driver.quit()

if __name__ == "__main__":
    main()
