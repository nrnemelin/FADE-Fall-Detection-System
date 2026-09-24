import paho.mqtt.client as mqtt
import time
import requests
import serial # <-- NEW: Added to read the physical USB connection

# 1. Setup the Broker connection
BROKER = "broker.emqx.io"
PORT = 1883
TOPIC = "fade_project/sensors/team_alert"
TELEGRAM_BOT_TOKEN = "8833819771:AAFg6k2M0h69DyJCrkn0ZCyyxBVpzOgDD3M"
TELEGRAM_CHAT_ID = "-5127138889"

def send_telegram_alert(alert_text):
    """Sends a push notification via Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": alert_text}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Failed to send Telegram alert: {e}")

# Setup MQTT Client
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

def on_connect(client, userdata, flags, rc):
    print(f"Connected to MQTT Broker with code {rc}")

client.on_connect = on_connect
client.connect(BROKER, PORT, 60)
client.loop_start()

# --- NEW: 2. Setup Serial Connection to Physical ESP32 ---
COM_PORT = 'COM5' # IMPORTANT: Change this to match your ESP32's port!
BAUD_RATE = 115200

try:
    esp32_serial = serial.Serial(COM_PORT, BAUD_RATE, timeout=1)
    print(f"Successfully connected to physical ESP32 on {COM_PORT}!")
except serial.SerialException:
    print(f"Error: Could not open {COM_PORT}. Is the Arduino Serial Monitor still open?")
    exit()

print("\n--- FADE Physical Sensor Bridge ---")
print("Listening for motion sensor data...")
print("Press Ctrl+C in terminal to quit.")
print("-----------------------------------\n")

try:
    while True:
        # Check if there is data waiting from the physical ESP32
        if esp32_serial.in_waiting > 0:
            # Read the incoming data, decode it, and remove extra spaces/newlines
            data = esp32_serial.readline().decode('utf-8').strip()
            
            # If the ESP32 sends the word "motion"
            if data == "motion":
                print(">> PHYSICAL MOTION DETECTED! Transmitting: Fall Alert!")
                
                # Trigger your FADE logic
                client.publish(TOPIC, "FALL", retain=False)
                # send_telegram_alert("⚠️ FADE ALERT: Fall detected by physical motion sensor!")
                
                # Pause briefly to prevent spamming your Telegram with hundreds 
                # of messages for a single movement
                time.sleep(3) 
        
        # Small sleep to keep your CPU usage low while it constantly checks
        time.sleep(0.1)

except KeyboardInterrupt:
    print("\nExiting program...")

finally:
    # Cleanly shut everything down when you stop the script
    client.loop_stop()
    client.disconnect()
    esp32_serial.close()
    print("Sensor Bridge Offline.")