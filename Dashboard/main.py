import flet as ft
from datetime import datetime
import paho.mqtt.client as mqtt 
import requests
import cv2
import threading
import collections
import time

# --- TELEGRAM BOT SETTINGS ---
TELEGRAM_BOT_TOKEN = "8833819771:AAFg6k2M0h69DyJCrkn0ZCyyxBVpzOgDD3M" 
TELEGRAM_CHAT_ID = "-5127138889" 

# --- VIDEO RECORDING SETTINGS ---
# MUST include :81/stream at the end! Update the IP if your hotspot assigns a new one.
ESP32_STREAM_URL = "http://172.20.10.6:81/stream" 

BUFFER_SECONDS = 30
FPS_ESTIMATE = 10  # ESP32-CAM streams at roughly 10 frames per second
MAX_FRAMES = BUFFER_SECONDS * FPS_ESTIMATE

# A deque automatically deletes the oldest frame when it hits the MAX_FRAMES limit
video_buffer = collections.deque(maxlen=MAX_FRAMES)
trigger_recording = False

def background_video_recorder():
    """Runs continuously in the background, keeping the last 30 seconds in memory."""
    global trigger_recording
    
    print("Connecting to ESP32 Camera Stream...")
    cap = cv2.VideoCapture(ESP32_STREAM_URL)
    
    while True:
        ret, frame = cap.read()
        
        # THE FIX: Properly reboot the stream if the connection drops!
        if not ret:
            print("⚠️ Stream connection lost! Reconnecting...")
            cap.release() # Release the dead connection
            time.sleep(2) # Give the network a breath
            cap = cv2.VideoCapture(ESP32_STREAM_URL) # Restart the connection
            continue
            
        # Add the current frame to our rolling memory buffer
        video_buffer.append(frame)
        
        # If the MQTT broker says "FALL", save the buffer to disk!
        if trigger_recording:
            trigger_recording = False
            save_and_send_video()

def save_and_send_video():
    """Saves the buffered frames to an MP4 and sends it to Telegram."""
    print("🚨 Saving Fall Recording...")
    frames_to_save = list(video_buffer)
    
    if not frames_to_save:
        print("No frames in buffer to save.")
        return

    # 1. Save the MP4 file
    height, width, _ = frames_to_save[0].shape
    fourcc = cv2.VideoWriter_fourcc(*'mp4v') # Format as MP4
    filename = "fall_incident.mp4"
    out = cv2.VideoWriter(filename, fourcc, FPS_ESTIMATE, (width, height))
    
    for f in frames_to_save:
        out.write(f)
    out.release()
    print("✅ Video saved to laptop!")

    # 2. Send the MP4 to the Relative's Telegram
    print("Transmitting video to Telegram...")
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo"
    
    try:
        with open(filename, 'rb') as video_file:
            files = {'video': video_file}
            data = {
                'chat_id': TELEGRAM_CHAT_ID, 
                'caption': '🚨 FALL DETECTED! Here is the 30 seconds of footage leading up to the event.'
            }
            requests.post(url, data=data, files=files)
        print("✅ Video sent to phone!")
    except Exception as e:
        print(f"Failed to send Telegram video: {e}")

def send_telegram_alert(alert_text):
    """Sends a push notification directly to the relative's phone via Telegram."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return 
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": alert_text}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Failed to send Telegram alert: {e}")

# -----------------------------

def main(page: ft.Page):
    page.title = "FADE Fall Detector"
    page.theme_mode = ft.ThemeMode.LIGHT
    
    # 1. Dynamic Status Card
    status_text = ft.Text("System Active", weight="bold", color="white")
    status_card = ft.Container(
        content=status_text,
        bgcolor="green", 
        padding=20,
        border_radius=10,
        alignment=ft.Alignment.CENTER
    )

    # 2. Alert History Log
    log_list = ft.ListView(expand=True, spacing=10, padding=20)

    # 3. Logging Logic (with Bulletproof Emojis Restored!)
    def add_log_entry(message, is_critical=False):
        timestamp = datetime.now().strftime("%I:%M:%S %p")

        # Update UI state and assign emoji based on event criticality
        if is_critical:
            status_card.bgcolor = "red"
            status_text.value = "ALERT: FALL DETECTED"
            icon_display = ft.Text("🚨", size=24) 
        else:
            status_card.bgcolor = "green"
            status_text.value = "System Active"
            icon_display = ft.Text("✅", size=24) 

        log_entry = ft.Card(
            content=ft.ListTile(
                leading=icon_display,
                title=ft.Text(message),
                subtitle=ft.Text(timestamp),
            )
        )
        log_list.controls.insert(0, log_entry)
        page.update()

   # 4. MQTT Integration (The Background Listener)
    def on_message(client, userdata, msg):
        global trigger_recording # <-- Allows the MQTT listener to trigger the video thread
        payload = msg.payload.decode("utf-8")
        
        # Trigger UI changes AND send Telegram alerts simultaneously
        if payload == "FALL":
            trigger_recording = True # <-- Instantly tells the background process to save the video!
            add_log_entry("Fall detected by ESP32 sensor!", is_critical=True)
            send_telegram_alert("🚨 URGENT: Fall detected by FADE sensor!") 
            
        elif payload == "VOICE":
            add_log_entry("Trigger word 'Aduh' detected by ESP32!", is_critical=True)
            send_telegram_alert("🚨 URGENT: Voice trigger 'Aduh' detected by FADE!")
            
        elif payload == "RESET":
            add_log_entry("Alert dismissed by hardware. System reset to normal.", is_critical=False)
            send_telegram_alert("✅ FADE Alert dismissed. System back to normal.")
            
        # 👇 NEW: Bathroom Panic Button Logic 👇
        elif payload == "PANIC":
            # NOTE: We do NOT trigger recording here to protect bathroom privacy!
            add_log_entry("Panic Button Pressed! Accident occur.", is_critical=True)
            send_telegram_alert("🚨 URGENT: Panic button is pressed. Accident occur.")

    # Connect to the MQTT Broker
    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    mqtt_client.on_message = on_message
    mqtt_client.connect("broker.emqx.io", 1883, 60)
    mqtt_client.subscribe("fade_project/sensors/team_alert")
    mqtt_client.loop_start() 

    # 5. UI Event Handlers (Manual Overrides for Testing)
    def simulate_fall(e):
        global trigger_recording
        trigger_recording = True # Also allows you to test the video save via the dashboard button!
        add_log_entry("Fall detected by manual simulation!", is_critical=True) 
        send_telegram_alert("🚨 TEST ALERT: Fall simulated from dashboard!") 

    def simulate_voice(e):
        add_log_entry("Trigger word 'Aduh' simulated!", is_critical=True)
        send_telegram_alert("🚨 TEST ALERT: Voice trigger simulated!")

    def reset_system(e):
        add_log_entry("Alert dismissed. System reset to normal.", is_critical=False)
        send_telegram_alert("✅ TEST: Alert dismissed manually.")

    # 6. Add all components to the page
    page.add(
        ft.AppBar(title=ft.Text("FADE Monitor")),
        status_card,
        ft.Row(
            controls=[
                ft.FilledButton("Simulate Fall", on_click=simulate_fall),
                ft.FilledButton("Simulate Voice", on_click=simulate_voice),
                ft.FilledButton("Dismiss Alert", on_click=reset_system, style=ft.ButtonStyle(bgcolor="blue", color="white")),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            wrap=True
        ),
        ft.Text("Alert History", weight="bold"),
        log_list
    )
    
    # Initialization Log
    add_log_entry("System initialized and MQTT listening.")

# Start the video recorder in a separate background thread BEFORE starting the UI
threading.Thread(target=background_video_recorder, daemon=True).start()

# ft.run(main)
ft.app(target=main)