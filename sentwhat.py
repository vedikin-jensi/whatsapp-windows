import time
import requests
import json
import os
import pyperclip
import argparse
import datetime
import mysql.connector
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import getpass
import random
import subprocess
import re
import zipfile
import io
import winreg
import platform
import shutil

# ==============================
#  AUTO UPDATE CHROMEDRIVER
# ==============================
LOCAL_DRIVER_PATH = r"D:\chromedriver"   # folder
CHROMEDRIVER_EXE = os.path.join(LOCAL_DRIVER_PATH, "chromedriver.exe")

# Ensure driver folder exists
os.makedirs(LOCAL_DRIVER_PATH, exist_ok=True)

def get_chrome_version():
    """Get installed Chrome version on Windows.
    Strategy:
    1) Registry BLBeacon (HKCU/HKLM) -> version
    2) `chrome --version` if on PATH
    3) Known installation paths -> `chrome.exe --version`
    4) `where chrome` fallback
    """
    # 1) Registry lookup
    reg_paths = [
        (winreg.HKEY_CURRENT_USER, r"Software\\Google\\Chrome\\BLBeacon", "version"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\\Google\\Chrome\\BLBeacon", "version"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\\WOW6432Node\\Google\\Chrome\\BLBeacon", "version"),
    ]
    for hive, subkey, value_name in reg_paths:
        try:
            with winreg.OpenKey(hive, subkey) as k:
                val, _ = winreg.QueryValueEx(k, value_name)
                if isinstance(val, str) and re.match(r"^\d+\.\d+\.\d+\.\d+$", val):
                    return val
        except OSError:
            pass

    # 2) Try PATH: `chrome --version`
    try:
        process = subprocess.Popen(
            "chrome --version",
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, shell=True
        )
        stdout = process.communicate()[0].decode("utf-8", errors="ignore")
        match = re.search(r"(\d+\.\d+\.\d+\.\d+)", stdout)
        if match:
            return match.group(1)
    except Exception:
        pass

    # 3) Known installation paths
    possible_paths = [
        r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        r"C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
        os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe"),
    ]
    for path in possible_paths:
        if os.path.exists(path):
            try:
                process = subprocess.Popen(
                    f'"{path}" --version',
                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, shell=True
                )
                stdout = process.communicate()[0].decode("utf-8", errors="ignore")
                match = re.search(r"(\d+\.\d+\.\d+\.\d+)", stdout)
                if match:
                    return match.group(1)
            except Exception:
                pass

    # 4) Last fallback: where chrome
    try:
        process = subprocess.Popen(
            "where chrome",
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, shell=True
        )
        stdout = process.communicate()[0].decode("utf-8", errors="ignore").strip().splitlines()
        if stdout:
            chrome_path = stdout[0].strip()
            process = subprocess.Popen(
                f'"{chrome_path}" --version',
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, shell=True
            )
            stdout2 = process.communicate()[0].decode("utf-8", errors="ignore")
            match = re.search(r"(\d+\.\d+\.\d+\.\d+)", stdout2)
            if match:
                return match.group(1)
    except Exception:
        pass

    return None


def get_driver_version_download_url(version):
    """Get ChromeDriver download URL matching the installed Chrome major version using
    Chrome for Testing known-good versions feed.
    """
    major = version.split(".")[0]
    feed_url = "https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json"
    resp = requests.get(feed_url, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    # Determine platform key
    system = platform.system().lower()
    if system == "windows":
        plat = "win64" if platform.machine().endswith("64") else "win32"
    elif system == "linux":
        plat = "linux64"
    elif system == "darwin":
        plat = "mac-x64"  # or mac-arm64 for M1/M2 Macs
    else:
        raise Exception(f"Unsupported OS: {system}")


    candidates = [v for v in data.get("versions", []) if v.get("version", "").startswith(f"{major}.")]
    if not candidates:
        raise Exception(f"❌ No ChromeDriver entries found for major version {major} in known-good versions feed.")

    # Pick the latest by version string (safe because feed is chronological), take the last
    chosen = candidates[-1]
    for item in chosen.get("downloads", {}).get("chromedriver", []):
        if item.get("platform") == plat:
            return item.get("url")

    raise Exception(f"❌ No ChromeDriver download for platform {plat} and major {major}.")

def update_chromedriver():
    chrome_version = get_chrome_version()
    if not chrome_version:
        raise Exception("❌ Could not detect installed Chrome version.")

    print(f"🟢 Installed Chrome version: {chrome_version}")

    download_url = get_driver_version_download_url(chrome_version)
    print(f"⬇️ Downloading latest chromedriver from: {download_url}")

    response = requests.get(download_url, timeout=60)
    if response.status_code != 200:
        raise Exception(f"❌ Failed to download ChromeDriver (HTTP {response.status_code}). URL: {download_url}")
    # Extract to a temporary subfolder to avoid mixing with existing files
    tmp_dir = os.path.join(LOCAL_DRIVER_PATH, "_tmp_extract")
    try:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        os.makedirs(tmp_dir, exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            z.extractall(tmp_dir)
    except Exception as e:
        raise Exception(f"❌ Failed to extract ChromeDriver archive: {e}")

    # Locate chromedriver.exe inside extracted content and move to CHROMEDRIVER_EXE
    found = None
    for root, dirs, files in os.walk(tmp_dir):
        for f in files:
            if f.lower() == "chromedriver.exe":
                found = os.path.join(root, f)
                break
        if found:
            break

    if not found or not os.path.exists(found):
        # Debug: list extracted files
        extracted = []
        for root, dirs, files in os.walk(tmp_dir):
            for f in files:
                extracted.append(os.path.relpath(os.path.join(root, f), tmp_dir))
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise Exception("❌ Downloaded archive did not contain chromedriver.exe. Extracted files: " + ", ".join(extracted))

    try:
        if os.path.exists(CHROMEDRIVER_EXE):
            os.remove(CHROMEDRIVER_EXE)
        # Copy without preserving metadata to avoid Windows CopyFile2 quirks
        shutil.copyfile(found, CHROMEDRIVER_EXE)
    except Exception as e:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise Exception(f"❌ Failed to place chromedriver.exe: {e}")
    finally:
        # Cleanup temp dir
        shutil.rmtree(tmp_dir, ignore_errors=True)

    print(f"✅ ChromeDriver updated at: {CHROMEDRIVER_EXE}")

# Always check & update before starting
update_chromedriver()

BASE_URL_CONFIG = "https://demo.thcitsolutions.com/aastha-pms/"

wait_time = random.randint(8*60, 13*60)
parser = argparse.ArgumentParser(description="Run WhatsApp Web automation with a dynamic profile ")
parser.add_argument("profile_name", help="Name of the Chrome profile to use/create")
args = parser.parse_args()
current_user = getpass.getuser()
base_profile_path = rf"chrome_profiles"
chrome_profile_path = os.path.abspath(os.path.join(base_profile_path, args.profile_name))

if not os.path.exists(chrome_profile_path):
    os.makedirs(chrome_profile_path)
    print(f"Created new Chrome profile: {chrome_profile_path}")
else:
    print(f"Using existing Chrome profile: {chrome_profile_path}")

# Chrome options
options = Options()
options.add_argument(f"--user-data-dir={chrome_profile_path}")
options.add_argument("--profile-directory=Default")
options.add_argument("--disable-extensions")
options.add_argument("--disable-gpu")
options.add_argument("--no-first-run")
options.add_argument("--no-default-browser-check")
options.add_argument("--remote-debugging-port=0")
options.add_argument("--disable-software-rasterizer")
options.add_experimental_option("detach", True)

# Use local driver
service = Service(CHROMEDRIVER_EXE)
browser = webdriver.Chrome(service=service, options=options)

BASE_URL = "https://web.whatsapp.com/"
def get_db_connection():
    return mysql.connector.connect(
        #host='vps1.vedikin.com',
        #user='thci_user_aastha_pms',
        #password='n^IOsBn3M2pqd3hO',
        #database='thci_db_aastha_pms'
        
        host='localhost',
        user='usr_aastha_pms_demo',
        password='teWg2su9qbCxCgX',
        database='db_aastha_pms_demo'
        
        #host='vps1.vedikin.com',
        #user='thci_user_aastha_pms',
        #password='n^IOsBn3M2pqd3hO',
        #database='thci_db_aastha_pms'

        # host= 'localhost',
        # user= 'root',
        # password= '',  # WAMP default password
        # database= 'aastha',  # Your database name
        # port= 3306,
        # charset= 'utf8mb4',
        # use_unicode= True
    )

def fetch_scheduled_messages():
    """Fetches scheduled messages that are due and have not been sent yet."""
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    
    current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    cursor.execute("""
        SELECT shed_id, phone_number, message, schedule_time, media
        FROM tbl_what_que 
        WHERE schedule_time <= %s AND is_sent = 0 
        ORDER BY schedule_time ASC
        LIMIT 5
    """, (current_time,))  # Ensure parameter is passed as a tuple
    
    messages = cursor.fetchall()
    cursor.close()
    connection.close()
    
    return messages

def update_scheduled_message(shed_id):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("UPDATE tbl_what_que SET is_sent = 1 WHERE shed_id = %s", (shed_id,))
    connection.commit()  # Save changes
    cursor.close()
    connection.close()

def send_scheduled_messages():
    """Heartbeat check before reading messages"""
    heartbeat_url = "https://dev.thcitsolutions.com/heartbeat-api/api.php"
    heartbeat_payload = {
        "authentication_token": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2g3h4i5j6k7l8m9n0o1p2q3r4s5t6u7v8w9x0y1z2",
        "product_name": "whatsapp-demo",
        "env": "demo",
        "website_url": "https://whatsapp-demo"
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
        print(f"❌ Heartbeat API call failed: {e}")  # ERROR DEBUG 1
        return []
    """Sends scheduled messages at the correct time."""
    print("\n🔍 Starting send_scheduled_messages()")
    print(f"🕒 Current time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    messages = fetch_scheduled_messages()
    print(f"ℹ️ Found {len(messages)} messages to send")
    
    if not messages:
        print("ℹ️ No scheduled messages to send at this time")
        return
    
    for msg in messages:
        try:
            
            phone = msg['phone_number']
            text = msg['message'].replace('##BASE_URL##', BASE_URL_CONFIG)  # Replace placeholder with actual URL
            media = msg.get('media', None)
            shed_id = msg['shed_id']
            scheduled_time = msg['schedule_time']
            
            print(f"\n📩 Processing message ID: {shed_id}")
            print(f"📱 To: {phone}")
            print(f"⏰ Scheduled for: {scheduled_time}")
            print(f"💬 Message: {text[:50]}..." if len(text) > 50 else f"💬 Message: {text}")
            print(f"🖼️ Media: {media if media else 'None'}")
            

            if media:  # If media exists, send image with message
                media_path = os.path.join(BASE_MEDIA_PATH, media)
                print(f"📎 Media path: {media_path}")
                if os.path.exists(media_path):
                    print("✅ Media file found")
                    send_whatsapp_image_with_message(phone, media_path, text)
                else:
                    print(f"❌ Media file not found: {media_path}")
                    continue  # Skip this message if media is missing
            else:  # Otherwise, send text message only
                print("📤 Sending text message...")
                send_whatsapp_message(phone, text, is_refresh=True)
            
            # Update the message status in database
            update_scheduled_message(shed_id)
            print(f"✅ Successfully sent and updated message ID: {shed_id}")
            
        except Exception as e:
            print(f"❌ Error processing message ID {shed_id}: {str(e)}")  # ERROR DEBUG 2
            import traceback
            traceback.print_exc()
    
    print("✅ Finished processing all scheduled messages\n")

def send_whatsapp_message(phone, message,is_refresh=False):
    global browser
    def is_valid_number(phone):
        return len(phone) == 12 and phone.startswith("91")

    if not is_valid_number(phone):
        print(f"❌ Invalid phone number: {phone}")
        return
    
    print(f"📨 Sending message to {phone}: {message}")
    
    if is_refresh == True:
        browser.get(f"https://web.whatsapp.com/send?phone={phone}")
    # try:
    #     chat_box = WebDriverWait(browser, 10).until(
    #         EC.presence_of_element_located((By.CSS_SELECTOR, '[aria-label="Type a message"], [aria-placeholder="Type a message"]'))
    #     )
    # except Exception:
    #     print("❌ Page took too long to load. Continuing further.")
    # else:
    #     print("✅ Page loaded quickly. Continuing further.")

    try:
        try:
            WebDriverWait(browser, 10).until(
                EC.invisibility_of_element_located((By.CSS_SELECTOR, "div[role='dialog']"))
            )
        except Exception:
            pass

        chat_box = WebDriverWait(browser, 20).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '[aria-label="Type a message"], [aria-placeholder="Type a message"]'))
        )

        pyperclip.copy(message)
        chat_box.click()
        chat_box.click()
        time.sleep(1)
        chat_box.send_keys(Keys.CONTROL, 'v')
        time.sleep(1)

        # Send the message
        chat_box.send_keys(Keys.ENTER)
        time.sleep(1)

        print(f"✅ Message sent to {phone}")
        return {"status": "success", "phone": phone, "message": "Message sent successfully"}

    except Exception as e:
        print(f"❌ Failed to send message to {phone}: {e}")  # ERROR DEBUG 3
        return {"status": "error", "phone": phone, "message": str(e)}

# Open WhatsApp Web
browser.get(BASE_URL)
print("🔄 Please log in to WhatsApp Web. Timeout: 120 seconds.") 

try:
    wait = WebDriverWait(browser, 120)
    wait.until(EC.presence_of_element_located((By.XPATH, "//div[@contenteditable='true']")))
    print("✅ Logged in successfully.")
except Exception as e:
    print("❌ Timeout: User did not log in within the specified time.")
    exit()

# Main loop
while True:
    send_scheduled_messages() 
    time.sleep(wait_time)
