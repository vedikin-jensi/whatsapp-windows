import time
import requests
import json
import os
import pyperclip
import argparse
import datetime
import mysql.connector
import platform
import subprocess
import re
import zipfile
import io
import shutil
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import getpass
import random
from selenium.common.exceptions import SessionNotCreatedException

# ==============================
#  AUTO UPDATE CHROMEDRIVER
# ==============================
# Use system-installed ChromeDriver instead of custom path
# ==============================
#  AUTO UPDATE CHROMEDRIVER (Full Sync with System Chrome)
# ==============================
import stat

# ==============================
#  AUTO UPDATE CHROMEDRIVER (Chrome-for-Testing API)
# ==============================
CHROMEDRIVER_EXE = "/usr/bin/chromedriver"
TMP_DRIVER_PATH = "/tmp/chromedriver_download"

import stat
import re
import io
import zipfile
import shutil
import requests
import subprocess
import os

CHROMEDRIVER_EXE = "/usr/bin/chromedriver"
TMP_DRIVER_PATH = "/tmp/chromedriver_download"

# ----------------------------------------------------------------
#  Helper functions
# ----------------------------------------------------------------
def get_chrome_version_linux():
    """Detect installed Chrome version (google-chrome-stable / chromium)."""
    for cmd in ["google-chrome", "google-chrome-stable", "chromium-browser"]:
        try:
            out = subprocess.run([cmd, "--version"], stdout=subprocess.PIPE, text=True)
            if out.returncode == 0:
                m = re.search(r"([\d.]+)", out.stdout)
                if m:
                    return m.group(1)
        except FileNotFoundError:
            continue
    raise RuntimeError("Chrome not found on system")

def get_local_driver_version():
    """Read current /usr/bin/chromedriver version."""
    try:
        out = subprocess.run([CHROMEDRIVER_EXE, "--version"], stdout=subprocess.PIPE, text=True)
        m = re.search(r"([\d.]+)", out.stdout)
        return m.group(1) if m else None
    except Exception:
        return None

def get_latest_cft_driver():
    """Fetch latest stable ChromeDriver info from Chrome-for-Testing API."""
    meta_url = "https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json"
    r = requests.get(meta_url, timeout=10)
    r.raise_for_status()
    data = r.json()
    stable = data["channels"]["Stable"]
    version = stable["version"]
    for entry in stable["downloads"]["chromedriver"]:
        if entry["platform"] == "linux64":
            return version, entry["url"]
    return None, None

def download_and_replace_driver(driver_version, driver_url):
    """Download and replace current ChromeDriver binary."""
    print(f"⬇️  Downloading ChromeDriver {driver_version} …")
    os.makedirs(TMP_DRIVER_PATH, exist_ok=True)
    r = requests.get(driver_url, stream=True, timeout=30)
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        z.extractall(TMP_DRIVER_PATH)
    new_path = os.path.join(TMP_DRIVER_PATH, "chromedriver-linux64", "chromedriver")
    os.chmod(new_path, 0o755)
    subprocess.run(["sudo", "mv", new_path, CHROMEDRIVER_EXE], check=True)
    subprocess.run(["sudo", "chmod", "755", CHROMEDRIVER_EXE], check=True)
    shutil.rmtree(TMP_DRIVER_PATH, ignore_errors=True)
    print(f"✅ ChromeDriver updated → {driver_version}")


def check_and_sync_chrome_versions():
    """
    1️⃣  Check both Chrome & ChromeDriver versions
    2️⃣  If mismatch → update both to latest stable
    3️⃣  Confirm after update
    """
    try:
        chrome_ver = get_chrome_version_linux()
        driver_ver = get_local_driver_version()
        remote_ver, remote_url = get_latest_cft_driver()

        print("===============================================")
        print(f"🧩 Installed Chrome version     : {chrome_ver}")
        print(f"🧩 Installed ChromeDriver version: {driver_ver or 'Not found'}")
        print(f"🌐 Latest Stable (CfT) version   : {remote_ver}")
        print("===============================================")

        if not chrome_ver:
            print("❌ Chrome not found. Install google-chrome-stable first.")
            return

        if not driver_ver:
            print("⚠️ ChromeDriver not found — installing latest stable version.")
            download_and_replace_driver(remote_ver, remote_url)
            return

        chrome_major = chrome_ver.split('.')[0]
        driver_major = driver_ver.split('.')[0]

        if chrome_major == driver_major:
            print(f"✅ Chrome and ChromeDriver match (v{chrome_major}) — no update needed.")
            return

        print(f"⚠️ Version mismatch → Chrome={chrome_major}, Driver={driver_major}")
        print("🔄 Updating Chrome + ChromeDriver to latest stable version…")

        # Update Chrome first
        subprocess.run(["sudo", "apt-get", "update", "-y"], check=False)
        subprocess.run(["sudo", "apt-get", "install", "--only-upgrade", "google-chrome-stable", "-y"], check=False)

        # Then update ChromeDriver to match
        download_and_replace_driver(remote_ver, remote_url)

        # Verify
        new_chrome = get_chrome_version_linux()
        new_driver = get_local_driver_version()
        print("-----------------------------------------------")
        print(f"✅ Chrome after update     : {new_chrome}")
        print(f"✅ ChromeDriver after update: {new_driver}")
        if new_chrome.split('.')[0] == new_driver.split('.')[0]:
            print("🎯 Sync successful — Chrome & Driver now aligned.")
        else:
            print("⚠️ Still mismatched. Consider freezing both versions manually.")

    except Exception as e:
        print(f"❌ Version sync failed: {e}")
        import traceback; traceback.print_exc()

# ----------------------------------------------------------------
#  Execute before launching Selenium
# ----------------------------------------------------------------
check_and_sync_chrome_versions()


def get_chrome_version_linux():
    """Detect installed Chrome version."""
    for cmd in ["google-chrome", "google-chrome-stable", "chromium-browser"]:
        try:
            out = subprocess.run([cmd, "--version"], stdout=subprocess.PIPE, text=True)
            if out.returncode == 0:
                m = re.search(r"([\d.]+)", out.stdout)
                if m:
                    return m.group(1)
        except FileNotFoundError:
            continue
    raise RuntimeError("Chrome not found")

def get_local_driver_version():
    """Read current /usr/bin/chromedriver version."""
    try:
        out = subprocess.run([CHROMEDRIVER_EXE, "--version"], stdout=subprocess.PIPE, text=True)
        m = re.search(r"([\d.]+)", out.stdout)
        return m.group(1) if m else None
    except Exception:
        return None

def get_latest_cft_driver():
    """Query Chrome-for-Testing API for the latest stable ChromeDriver."""
    meta_url = "https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json"
    r = requests.get(meta_url, timeout=10)
    r.raise_for_status()
    data = r.json()
    stable = data["channels"]["Stable"]
    version = stable["version"]
    for entry in stable["downloads"]["chromedriver"]:
        if entry["platform"] == "linux64":
            return version, entry["url"]
    return None, None

def download_and_replace_driver(driver_version, driver_url):
    """Download and replace the current ChromeDriver binary."""
    # print(f"⬇️  Downloading ChromeDriver {driver_version}")
    r = requests.get(driver_url, stream=True, timeout=30)
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        z.extractall(TMP_DRIVER_PATH)
    new_path = os.path.join(TMP_DRIVER_PATH, "chromedriver-linux64", "chromedriver")
    os.chmod(new_path, 0o755)
    subprocess.run(["sudo", "mv", new_path, CHROMEDRIVER_EXE], check=True)
    subprocess.run(["sudo", "chmod", "755", CHROMEDRIVER_EXE], check=True)
    shutil.rmtree(TMP_DRIVER_PATH, ignore_errors=True)
    # print(f"✅ Updated ChromeDriver → {driver_version}")

def ensure_latest_chromedriver():
    """Main updater logic."""
    chrome_ver = get_chrome_version_linux()
    local_ver = get_local_driver_version()
    print(f"Detected Chrome version: {chrome_ver}")
    # print(f"Current ChromeDriver version: {local_ver or 'None'}")

    remote_ver, remote_url = get_latest_cft_driver()
    if not remote_ver:
        print("⚠️ Could not fetch version info from CfT API.")
        return

    print(f"Latest ChromeDriver from CfT: {remote_ver}")
    if local_ver != remote_ver:
        print("🔄 Updating ChromeDriver …")
        download_and_replace_driver(remote_ver, remote_url)
    else:
        print("✅ ChromeDriver already up-to-date.")

# Run updater before Selenium starts
ensure_latest_chromedriver()



# Add ChromeDriver to PATH if not already there
os.environ["PATH"] += os.pathsep + os.path.dirname(CHROMEDRIVER_EXE)

BASE_URL_CONFIG = "https://pms.aasthatechno.in"

# wait_time = random.randint(8*60, 13*60)
parser = argparse.ArgumentParser(description="Run WhatsApp Web automation with a dynamic profile ")
parser.add_argument("profile_name", help="Name of the Chrome profile to use/create")
args = parser.parse_args()
current_user = getpass.getuser()
base_profile_path = rf"chrome_profiles"
chrome_profile_path = os.path.join(base_profile_path, args.profile_name)

if not os.path.exists(chrome_profile_path):
    os.makedirs(chrome_profile_path)
    print(f"Created new Chrome profile: {chrome_profile_path}")
else:
    print(f"Using existing Chrome profile: {chrome_profile_path}")

options = Options()
options.add_argument(f"--user-data-dir={os.path.abspath(chrome_profile_path)}")
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--remote-allow-origins=*')

# Use the local ChromeDriver
service = Service(executable_path=CHROMEDRIVER_EXE)
try:
    browser = webdriver.Chrome(service=service, options=options)
except SessionNotCreatedException as e:
    print("❌ Session not created due to driver/browser mismatch. If the local ChromeDriver exists and is on PATH, remove or rename it, then retry.")
    raise
BASE_URL = "https://web.whatsapp.com/"


def get_db_connection():
    try:
        return mysql.connector.connect(
            # host='',
            # port='',
            # user='',
            # password='',
            # database=''

        )
    except Exception as e:
        print("⚠️ Database connection failed:", e)
        import traceback; traceback.print_exc()
        return None


def fetch_scheduled_messages():
    try:
        connection = get_db_connection()
        if connection is None:
            return []

        cursor = connection.cursor(dictionary=True)
        current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        cleanup_sql = """
            UPDATE tbl_what_que
            SET is_sent = 1
            WHERE is_sent = 0 AND (message IS NULL OR TRIM(message) = '')
        """
        cursor.execute(cleanup_sql)
        connection.commit()

        cursor.execute("""
            SELECT shed_id, phone_number, message, schedule_time, media
            FROM tbl_what_que 
            WHERE schedule_time <= %s AND is_sent = 0
              AND message IS NOT NULL AND TRIM(message) <> ''
            ORDER BY schedule_time ASC
            LIMIT 5
        """, (current_time,))

        messages = cursor.fetchall()
        return messages

    except Exception as e:
        # print("❌ Error fetching scheduled messages:", e)
        import traceback; traceback.print_exc()
        return []

    finally:
        try:
            cursor.close()
            connection.close()
        except:
            pass

def update_scheduled_message(shed_id):
    try:
        connection = get_db_connection()
        if connection is None:
            return
        cursor = connection.cursor()
        cursor.execute("UPDATE tbl_what_que SET is_sent = 1 WHERE shed_id = %s", (shed_id,))
        connection.commit()
    except Exception as e:
        # print(f"⚠️ Failed to update message ID {shed_id}: {e}")
        import traceback; traceback.print_exc()
    finally:
        try:
            cursor.close()
            connection.close()
        except:
            pass


def send_scheduled_messages():
    """Heartbeat check before reading messages"""
    heartbeat_url = "https://dev.thcitsolutions.com/heartbeat-api/api.php"
    heartbeat_payload = {
        "authentication_token": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2g3h4i5j6k7l8m9n0o1p2q3r4s5t6u7v8w9x0y1z2",
        "product_name": "whatsapp-aastha-live",
        "env": "Live",
        "website_url": ""
    }
    try:
        # print("Sending heartbeat...")
        resp = requests.post(heartbeat_url, json=heartbeat_payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        # print("Heartbeat API response:", data)
        if data.get("status") != "success":
            print("❌ Heartbeat API did not return success. Proceeding to send messages anyway.")
    except Exception as e:
        print(f"❌ Heartbeat API call failed: {e} - Proceeding to send messages anyway.")  
    """Sends scheduled messages at the correct time."""
    # print("\n🔍 Starting send_scheduled_messages()")
    # print(f"🕒 Current time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    messages = fetch_scheduled_messages()
    print(f"ℹ️ Found {len(messages)} messages to send")
    
    if not messages:
        print("ℹ️ No scheduled messages to send at this time")
        return
    
    for msg in messages:
        try:
            
            phone = msg['phone_number']
            # Handle NULL/empty messages: skip sending but mark as sent
            text_raw = msg.get('message')
            if text_raw is None or str(text_raw).strip() == '':
                shed_id = msg['shed_id']
                print(f"⚠️ Skipping NULL/empty message. Marking as sent. ID: {shed_id}")
                update_scheduled_message(shed_id)
                continue

            # Safe replacement when message is non-null
            text = str(text_raw).replace('##BASE_URL##', BASE_URL_CONFIG)  # Replace placeholder with actual URL
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
        time.sleep(random.randint(8, 13))

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

import traceback

while True:
    try:
        send_scheduled_messages()
    except Exception as e:
        print("❌ Unhandled exception in main loop:", e)
        traceback.print_exc()
        print("🔁 Restarting after 30 seconds...")
        time.sleep(30)
        continue

    time.sleep(5 * 60)


