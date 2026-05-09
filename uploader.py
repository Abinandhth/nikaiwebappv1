import serial
import time
import requests

SERIAL_PORT = 'COM5'
BAUD_RATE = 9600

# YOUR RENDER DOMAIN
API_URL = 'https://nikaiwebappv1.onrender.com/sensor/data/'

# reconnect delay
RETRY_DELAY = 5


# maps Arduino data labels
sensor_types = {
    'kit1': 'Ammonia',
    'kit2': 'Smoke',
    'kit3': 'Footfall',
    'kit4': 'Moisture'
}


def send_to_cloud(sensor_id, value):

    payload = {
        'sensor_id': sensor_id,
        'value': value
    }

    try:
        response = requests.post(API_URL, json=payload)

        print(f"Uploaded -> {payload}")
        print(f"Server response: {response.text}")

    except Exception as e:
        print(f"Upload error: {e}")



def parse_line(line):

    print(f"Raw: {line}")

    parts = line.split()

    data = {}

    for part in parts:
        if ':' in part:
            key, value = part.split(':', 1)
            data[key.strip()] = value.strip()

    for kit_key, sensor_type_name in sensor_types.items():

        sensor_id = data.get(kit_key)
        value_str = data.get(sensor_type_name)

        if sensor_id and value_str:

            try:
                value = float(value_str)
                send_to_cloud(sensor_id, value)
            except ValueError:
                print(f"Invalid value: {value_str}")



def main():
    while True:
        try:
            with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1) as ser:
                print(f"Connected to {SERIAL_PORT}")

                while True:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        parse_line(line)

        except serial.SerialException as e:
            print(f"Serial error: {e}")
            print(f"Retrying in {RETRY_DELAY} seconds...")
            time.sleep(RETRY_DELAY)

        except KeyboardInterrupt:
            print("Stopped by user.")
            break


if __name__ == "__main__":
    main()
