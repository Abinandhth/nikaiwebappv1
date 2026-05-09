import os
import sys
import django
import requests
import time

# =====================================================
# DJANGO SETUP
# =====================================================

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault(
    'DJANGO_SETTINGS_MODULE',
    'myproject.settings'
)

django.setup()

# =====================================================
# IMPORT MODELS
# =====================================================

from landing.models import Restroom, Alert
from django.utils.timezone import now

# =====================================================
# TELEGRAM BOT CONFIG
# =====================================================

BOT_TOKEN = "8665192200:AAE5smQtNVqj0xBpyBiebr2J_LjJ9WXW8D4"

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# =====================================================
# GET TELEGRAM UPDATES
# =====================================================

def get_updates(offset=None):

    url = f"{BASE_URL}/getUpdates"

    params = {
        "timeout": 30
    }

    if offset:
        params["offset"] = offset

    response = requests.get(url, params=params)

    return response.json()

# =====================================================
# SEND TELEGRAM MESSAGE
# =====================================================

def send_message(chat_id, text):

    url = f"{BASE_URL}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": text
    }

    requests.post(url, data=payload)

# =====================================================
# PROCESS INCOMING MESSAGE
# =====================================================

def process_message(message):

    try:

        # Telegram group ID
        chat_id = str(message["chat"]["id"])

        # User message
        text = message.get("text", "").strip().lower()

        print(f"\nMessage received")
        print(f"Group ID: {chat_id}")
        print(f"Message: {text}")

        # =================================================
        # CHECK IF MESSAGE IS "resolved"
        # =================================================

        if text == "resolved":

            print("Checking restroom linked to this group...")

            # Find restroom linked to telegram group
            restroom = Restroom.objects.filter(
                group_id=chat_id
            ).first()

            # If no restroom found
            if not restroom:

                print("No restroom linked to this group.")

                send_message(
                    chat_id,
                    "❌ No restroom linked to this Telegram group."
                )

                return

            print(f"Restroom found: {restroom.name}")

            # =================================================
            # GET TODAY'S DATE
            # =================================================

            today = now().date()

            # =================================================
            # UPDATE ALL TODAY'S ALERTS
            # =================================================

            updated_count = Alert.objects.filter(
                restroom=restroom,
                created_at__date=today,
                resolved=False
            ).update(resolved=True)

            print(f"{updated_count} alerts resolved.")

            # =================================================
            # SEND CONFIRMATION MESSAGE
            # =================================================

            send_message(
                chat_id,
                f"✅ {updated_count} alerts marked as resolved for today."
            )

    except Exception as e:

        print(f"Error processing message: {e}")

# =====================================================
# MAIN BOT LOOP
# =====================================================

def main():

    print("Telegram listener started...")

    update_id = None

    while True:

        try:

            # Get new telegram messages
            data = get_updates(update_id)

            if data["ok"]:

                for item in data["result"]:

                    # Prevent reading same message again
                    update_id = item["update_id"] + 1

                    # Check if message exists
                    if "message" in item:

                        process_message(item["message"])

            time.sleep(1)

        except Exception as e:

            print(f"Main loop error: {e}")

            time.sleep(5)

# =====================================================
# START PROGRAM
# =====================================================

if __name__ == "__main__":
    main()