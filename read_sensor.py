import serial
import os
import django
import sys
import time
import requests

# -------------------- DJANGO SETUP --------------------

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')
django.setup()

from landing.models import Sensor, SensorReading , Alert, Restroom
# -------------------- CONFIGURATION --------------------

SERIAL_PORT = 'COM5'
BAUD_RATE = 9600

THRESHOLD = 600         # Smoke threshold
ALERT_DURATION = 60      # 60 seconds continuous high
COOLDOWN = 120           # 2 minutes before next alert
DB_SAVE_INTERVAL = 10 
ALERT_DELAY = 5   # seconds between alerts

last_alert_times = {}  # track per sensor   # Save to DB every 10 seconds

# Telegram
TELEGRAM_TOKEN = "8665192200:AAE5smQtNVqj0xBpyBiebr2J_LjJ9WXW8D4"

# -------------------- GLOBAL VARIABLES --------------------

above_threshold_start = None
last_alert_time = 0
last_db_save_time = 0
last_sensor_values = {} # Store last saved value per sensor kit
last_sensor_save_times = {} # Store last save time per sensor kit
SAVE_INTERVAL = 60 # Force save every 60 seconds even if value hasn't changed

# -------------------- TELEGRAM FUNCTION --------------------

def send_telegram_alert(message, chat_id):
    if not chat_id:
        print("⚠️ No chat_id provided for Telegram alert.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message
    }
    try:
        requests.post(url, data=payload)
        print("🚨 Telegram alert sent!")
    except Exception as e:
        print(f"Telegram error: {e}")

# -------------------- DATA PARSE FUNCTION --------------------

def parse_and_process(line):
    global above_threshold_start, last_alert_time, last_db_save_time, last_sensor_values, last_sensor_save_times

    # Example Format: kit1:kit1_value Ammonia:ammonia_value kit2:kit2_value smoke:smoke_value kit3:kt3_value footfall:footfall_value kit4:kit4_value moisture:moisture_value
    parts = line.split()
    data = {}

    for part in parts:
        if ':' in part:
            key, value = part.split(':', 1)
            data[key.strip()] = value.strip()

    sensor_types = {
        'kit1': 'Ammonia',
        'kit2': 'Smoke',
        'kit3': 'Footfall',
        'kit4': 'Moisture'
    }

    current_time = time.time()
    
    for kit_key, sensor_type_name in sensor_types.items():
        kit_id = data.get(kit_key)
        sensor_value_str = data.get(sensor_type_name)
        
        if kit_id and sensor_value_str:
            try:
                sensor_value = float(sensor_value_str)
            except ValueError:
                print(f"⚠️ Invalid value for {sensor_type_name}: {sensor_value_str}")
                continue

            # In the DB: Sensor.sensor_id corresponds to 'kit_id'
            sensor = Sensor.objects.filter(sensor_id=kit_id).first()
            if sensor:
                # Check if we should save this reading to avoid flooding the DB
                sensor_key = f"{kit_id}_{sensor_type_name}"
                last_val = last_sensor_values.get(sensor_key)
                last_time = last_sensor_save_times.get(sensor_key, 0)
                
                # Determine value change threshold (Footfall needs to be exact, others can have slight noise filter)
                value_changed = False
                if last_val is None:
                    value_changed = True
                elif sensor_type_name == 'Footfall' and sensor_value != last_val:
                    value_changed = True # Any change in footfall is a new person
                elif sensor_type_name != 'Footfall' and abs(sensor_value - last_val) > 0.5:
                    value_changed = True # Small noise filter for analog sensors
                    
                time_elapsed = current_time - last_time > SAVE_INTERVAL
                
                if value_changed or time_elapsed:
                    reading = SensorReading.objects.create(
                        sensor=sensor,
                        value=sensor_value
                    )
                    print(f"💾 Saved {sensor_type_name} to DB: {sensor_value} for Kit: {kit_id}")
                    last_sensor_values[sensor_key] = sensor_value
                    last_sensor_save_times[sensor_key] = current_time
                    
                    # Check threshold
                    threshold_limit = sensor.threshold_max or THRESHOLD
                    if sensor_value > threshold_limit:
    
                        alert_key = f"alert_{sensor_key}"
                        last_alert_t = last_alert_times.get(alert_key, 0)
    
                        # allow alert only if delay passed
                        if current_time - last_alert_t >= ALERT_DELAY:
    
                            print(f"⚠️ Threshold crossed for {sensor_type_name}! Value: {sensor_value} > {threshold_limit}")
    
                            restroom = sensor.restroom
                            if restroom:
                                msg = f"🚨 {sensor_type_name} HIGH in {restroom.name}!\nCurrent Value: {sensor_value}"
    
                                alert = Alert.objects.create(
                                    message=msg,
                                    restroom=restroom,
                                    sensor_reading=reading
                                )
    
                                chat_id = restroom.chat_id
                                if chat_id:
                                    send_telegram_alert(msg, chat_id)
    
                                # update last alert time
                                last_alert_times[alert_key] = current_time
            else:
                 print(f"⚠️ Sensor '{kit_id}' not found in DB")


# -------------------- MAIN LOOP --------------------

def main():
    print(f"Connecting to {SERIAL_PORT}...")

    while True:
        try:
            ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
            print("✅ Connected to Arduino")

            while True:
                if ser.in_waiting > 0:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()

                    if line:
                        print(f"Raw: {line}")
                        parse_and_process(line)

                time.sleep(0.1)

        except serial.SerialException as e:
            print(f"Serial error: {e}")
            print("Retrying in 5 seconds...")
            time.sleep(5)

        except KeyboardInterrupt:
            print("\nStopping program...")
            if 'ser' in locals() and ser.is_open:
                ser.close()
            break


if __name__ == '__main__':
    main()