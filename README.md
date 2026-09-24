# FADE: Smart Fall Detection & IoT Monitoring System

Engineered an end-to-end IoT fall detection system designed to monitor elderly individuals living alone and alert remote family members during emergencies[cite: 18]. This system bridges physical edge sensors with a real-time monitoring dashboard and a cloud-based notification pipeline[cite: 18].

## Key Features & Architecture

* **Hardware Integration:** Powered by an ESP32-S3 microcontroller processing contextual awareness via an HC-SR501 PIR motion sensor and event-based validation via an INMP441 microphone (detecting distress trigger words like "Aduh!")[cite: 18].
* **Privacy-First Design:** Features a portable wireless panic button utilizing an ESP32-C3 SuperMini, specifically designed for high-risk, high-privacy areas like bathrooms[cite: 18].
* **Wireless Data Routing:** Establishes a robust communication bridge using the MQTT protocol (`broker.emqx.io`) to seamlessly transmit payload data from the hardware edge to the central Python dashboard[cite: 14, 18].
* **IoT Architecture & UI:** Features a dynamic monitoring dashboard built using Python and Flet, complete with real-time status cards and alert history logging[cite: 18].
* **NVR Video Buffering:** Utilizes OpenCV to engineer a 30-second local rolling video buffer, ensuring fall footage is captured and saved without relying on privacy-invasive 24/7 cloud recording[cite: 18].
* **Automated Alert Pipeline:** Integrates the Telegram Bot API to instantly push critical text alerts and 30-second MP4 video clips to a family group chat the moment a fall is detected[cite: 18].

## Setup & Installation

### 1. Hardware Firmware (C++)
* Flash the master edge code (`cam_sensor_mic.ino`) to the ESP32-S3 using the Arduino IDE.
* Flash the emergency panic button code to the ESP32-C3 SuperMini[cite: 11, 18].
* Ensure both boards are configured to your local Wi-Fi network to enable MQTT transmission.

### 2. Software Dashboard (Python)
1. Clone this repository and open the `FADE_App` directory.
2. Install the required dependencies:
   ```bash
   python -m pip install flet opencv-python paho-mqtt requests
