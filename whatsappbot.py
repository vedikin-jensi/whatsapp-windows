# -*- coding: utf-8 -*-
from email import message
import time
import requests
import json
import shutil
import os
import pyperclip
import argparse
import datetime
import mysql.connector
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium import webdriver
import time
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import getpass

wait_time = 60 * 5 #5 minutes
rest_time = 60 * 10 #10 minutes
# Static Configuration Variables
GROUP_1_NAME = "Survey Group"
GROUP_2_NAME = "Drafting Group"
BOT_TAG = "@VedikIn Dev"
#DESTINATION_PATH = r"E:\onedrivefiles"
DESTINATION_PATH = r"/home/dhokai-server/Documents/projects/aastha-whatsapp-demo/files"
BASE_URL = "https://web.whatsapp.com/"
# BASE_MEDIA_PATH = r"D:\git\n8n-workflows\whatsapp-message\uploads"
# FILE_URL_PREFIX = "https://yourdomain.com/onedrivefiles/"


# Parse command-line arguments
parser = argparse.ArgumentParser(description="Run WhatsApp Web automation with a dynamic profile")
parser.add_argument("profile_name", help="Name of the Chrome profile to use/create")
args = parser.parse_args()

# Define Chrome Profile Path dynamically
current_user = getpass.getuser()
# base_profile_path = rf"C:\Users\{current_user}\AppData\Local\Google\Chrome\User Data"
base_profile_path = rf"chrome_profiles"
chrome_profile_path = os.path.join(base_profile_path, args.profile_name)

# Ensure the profile directory exists
if not os.path.exists(chrome_profile_path):
    os.makedirs(chrome_profile_path)
    print(f" Created new Chrome profile: {chrome_profile_path}")
else:
    print(f" Using existing Chrome profile: {chrome_profile_path}")

# Set up Selenium Chrome options
options = Options()
options.add_argument(f"--user-data-dir={chrome_profile_path}")
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

browser = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
# browser = webdriver.Chrome(executable_path=r'D:\git\n8n-workflows\whatsapp-message\wenv\Scripts\chromedriver.exe', options=options)

def get_db_connection():
    return mysql.connector.connect(
        # host="localhost",
        # user="root",
        # password="",
        # database="n8n_follows"

        host='localhost',
        user='usr_aastha_pms_demo',
        password='teWg2su9qbCxCgX',
        database='db_aastha_pms_demo'
    )

def send_error_to_demo_group(filename):
    try:
        print(f"⚠️ Sending error message to '{GROUP_1_NAME}' for file: {filename}")
        browser.switch_to.window(browser.window_handles[0])

        search_box = WebDriverWait(browser, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]'))
        )
        search_box.click()
        search_box.clear()
        time.sleep(0.5)
        search_box.send_keys(GROUP_1_NAME)

        demo_group = WebDriverWait(browser, 10).until(
            EC.element_to_be_clickable((By.XPATH, f'//span[@title="{GROUP_1_NAME}"]'))
        )
        demo_group.click()
        print(f"✅ '{GROUP_1_NAME}' group selected for error message.")

        message_box = WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.XPATH, '//footer//div[@contenteditable="true"][@data-tab="10"]'))
        )
        message_box.click()
        error_message = f"❌ Something went wrong with {filename}"
        message_box.send_keys(error_message)
        message_box.send_keys(Keys.ENTER)
        print(f"🚨 Error message sent to {GROUP_1_NAME}: {error_message}")

    except Exception as e:
        print(f"❌ Failed to send error message to {GROUP_1_NAME}: {e}")

def store_link_in_db(link):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "INSERT INTO tbl_onedrive (one_link) VALUES (%s)"
        cursor.execute(query, (link,))
        conn.commit()
        print(f"💾 Stored link in database: {link}")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"❌ Failed to store link in database: {e}")

def get_latest_downloaded_file():
    downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
    print(f"📁 Checking Downloads folder: {downloads_path}")
    
    files = [os.path.join(downloads_path, f) for f in os.listdir(downloads_path) if os.path.isfile(os.path.join(downloads_path, f))]
    
    if not files:
        print("❌ No files found in Downloads folder.")
        return None
    
    latest_file = max(files, key=os.path.getctime)
    print(f"🆕 Latest downloaded file detected: {latest_file}")
    return latest_file

def file_already_downloaded(filename):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM tbl_onedrive WHERE one_link = %s AND is_dowloaded = 1", (filename,))
        return cursor.fetchone() is not None
    finally:
        cursor.close()
        conn.close()

def generate_sequential_filename():
    today = datetime.datetime.now().strftime('%Y%m%d')
    prefix = f"{today}_oo"
    print(f"🔢 Checking existing files in {DESTINATION_PATH} starting with '{prefix}'")

    existing = [f for f in os.listdir(DESTINATION_PATH) if f.startswith(prefix)]
    sequence_numbers = [int(f[len(prefix):]) for f in existing if f[len(prefix):].isdigit()]
    next_number = max(sequence_numbers, default=0) + 1

    new_filename = f"{prefix}{next_number}"
    print(f"📄 Generated new filename: {new_filename}")
    return new_filename

def move_and_rename_file_and_update_db(downloaded_file, onedrive_link):
    try:
        timestamp = datetime.datetime.now().strftime('%Y%m%d')
        base_name = f"{timestamp}_oo"
        count = 1
        extension = os.path.splitext(downloaded_file)[1]

        while True:
            new_file_name = f"{base_name}{count}{extension}"
            new_file_path = os.path.join(DESTINATION_PATH, new_file_name)
            if not os.path.exists(new_file_path):
                break
            count += 1

        shutil.move(downloaded_file, new_file_path)
        print(f"✅ Moved file to: {new_file_path}")

        # Update DB
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            query = "UPDATE tbl_onedrive SET file_name = %s, is_dowloaded = 1 WHERE one_link = %s"
            cursor.execute(query, (new_file_name, onedrive_link))
            conn.commit()
            print(f"💾 Updated database with file name: {new_file_name}")
            cursor.close()
            conn.close()
            return new_file_name
        except Exception as e:
            print(f"❌ Error updating DB: {e}")
            return None

    except Exception as e:
        print(f"❌ Error moving file or updating DB: {e}")
        return None

def send_message_to_demo2_group(message):
    try:
        print(f"📨 Switching to group '{GROUP_2_NAME}' to send confirmation...")
        browser.switch_to.window(browser.window_handles[0])

        search_box = WebDriverWait(browser, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]'))
        )
        search_box.click()
        search_box.clear()
        time.sleep(0.5)
        search_box.send_keys(GROUP_2_NAME)
        print(f"🔍 Searching for {GROUP_2_NAME} group...")

        demo2_group = WebDriverWait(browser, 10).until(
            EC.element_to_be_clickable((By.XPATH, f'//span[@title="{GROUP_2_NAME}"]'))
        )
        demo2_group.click()
        print(f"✅ '{GROUP_2_NAME}' group selected.")

        message_box = WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.XPATH, '//footer//div[@contenteditable="true"][@data-tab="10"]'))
        )
        message_box.click()
        message_box.send_keys(message)
        message_box.send_keys(Keys.ENTER)
        print(f"📤 Message sent to {GROUP_2_NAME}: {message}")

    except Exception as e:
        print(f"❌ Failed to send message to {GROUP_2_NAME}: {e}")

def process_onedrive_link_from_demo_group():
    """Heartbeat check before reading messages"""
    heartbeat_url = "https://dev.thcitsolutions.com/heartbeat-api/api.php"
    heartbeat_payload = {
        "authentication_token": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2g3h4i5j6k7l8m9n0o1p2q3r4s5t6u7v8w9x0y1z2",
        "product_name": "whatsapp-demo",
        "env": "demo",
        "website_url": "https://whatsapp-bot-demo"
    }
    try:
        print("Sending heartbeat...")
        resp = requests.post(heartbeat_url, json=heartbeat_payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        print("Heartbeat API response:", data)
        if data.get("status") != "success":
            print("❌ Heartbeat API did not return success.")
            return []
    except Exception as e:
        print(f"❌ Heartbeat API call failed: {e}")
        return []
    print(f"🔍 Looking for group chat named '{GROUP_1_NAME}'...")

    try:
        search_box = WebDriverWait(browser, 20).until(
            EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true']"))
        )
        search_box.clear()
        search_box.send_keys(GROUP_1_NAME)
        time.sleep(2)

        print(f"🔎 Selecting group chat '{GROUP_1_NAME}'...")
        demo_chat = browser.find_element(By.XPATH, f"//span[@title='{GROUP_1_NAME}']")
        demo_chat.click()
        time.sleep(3)

        print(f"✅ Opened '{GROUP_1_NAME}' group chat. Now checking messages...")
        chat_box = WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.ID, "main"))
        )
        all_messages = chat_box.find_elements(By.CSS_SELECTOR, "div.copyable-text")

        onedrive_link = None

        for message in reversed(all_messages[-20:]):
            try:
                text = message.text
                print(f"📨 Checking message: {text}")

                if BOT_TAG in text:
                    urls = re.findall(r"https?://[^\s]+", text)
                    for url in urls:
                        if "onedrive.live.com" in url:
                            onedrive_link = url
                            print(f"🔗 Found OneDrive link: {onedrive_link}")

                            if file_already_downloaded(onedrive_link):
                                print(f"⚠️ File '{onedrive_link}' already downloaded (is_dowloaded=1). Skipping.")
                                return  
                            break
            except Exception as e:
                print(f"⚠️ Error processing message: {e}")

            if onedrive_link:
                break

        if not onedrive_link:
            print(f"❌ No OneDrive link with {BOT_TAG} found in recent messages.")
            time.sleep(wait_time)
            return

        print(f"🌐 Opening OneDrive link: {onedrive_link}")
        browser.execute_script(f'''window.open("{onedrive_link}", "_blank");''')
        time.sleep(5)

        browser.switch_to.window(browser.window_handles[-1])
        print("🧭 Switched to OneDrive tab.")

        download_button = WebDriverWait(browser, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@title='Download' or @aria-label='Download']"))
        )
        print("⬇️ Download button found. Clicking it...")
        download_button.click()

        print("✅ Download initiated successfully.")
        store_link_in_db(onedrive_link)

        time.sleep(rest_time)

        downloaded_file = get_latest_downloaded_file()
        if downloaded_file:
            new_file_name = move_and_rename_file_and_update_db(downloaded_file, onedrive_link)
            if new_file_name:
                full_link = f"{DESTINATION_PATH}/{new_file_name}"
                message = f"Filed Added! {full_link}"
                print(f"📢 Preparing to send message to '{GROUP_2_NAME}': {message}")
                send_message_to_demo2_group(message)
            else:
                print("⚠️ Failed to move file or update DB.")
                send_error_to_demo_group(onedrive_link)
        else:
            print("⚠️ No file found to move.")
            send_error_to_demo_group("UnknownFile (download may have failed)")

        browser.switch_to.window(browser.window_handles[0])
        print("↩️ Switched back to WhatsApp tab.")
        if len(browser.window_handles) > 1:
            browser.switch_to.window(browser.window_handles[1])
            print("🧹 Closing OneDrive tab...")
            browser.close()
            browser.switch_to.window(browser.window_handles[0])

    except Exception as e:
        print(f"❌ Error in process: {e}")

# Open WhatsApp Web
browser.get(BASE_URL)
print("🔄 Please log in to WhatsApp Web. Timeout: 120 seconds.")

while True:
    process_onedrive_link_from_demo_group()
        # 🔄 Refresh WhatsApp Web to ensure latest state before next iteration
    try:
        browser.refresh()
        print("🔃 WhatsApp tab refreshed.")
    except Exception as refresh_err:
        print(f"⚠️ Failed to refresh WhatsApp tab: {refresh_err}")
    time.sleep(wait_time)