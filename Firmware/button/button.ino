#include <WiFi.h>
#include <PubSubClient.h>

// --- 1. Network & MQTT Configuration ---
const char* ssid = "emelin";           // Replace with your Wi-Fi name
const char* password = "aliflamlamha";   // Replace with your Wi-Fi password
const char* mqtt_server = "broker.emqx.io";    // Your project's existing broker

WiFiClient espClient;
PubSubClient client(espClient);

// --- 2. Hardware Configuration ---
const int BUTTON_PIN = 4; // We wired the button to D4
unsigned long lastDebounceTime = 0;
unsigned long debounceDelay = 1000; // 1-second delay to prevent double-triggering

void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Connecting to Wi-Fi: ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWiFi connected!");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());
}

void reconnect() {
  // Loop until we are reconnected to the MQTT broker
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    // Create a random client ID for this specific bathroom node
    String clientId = "FADE_BathroomNode-";
    clientId += String(random(0xffff), HEX);
    
    if (client.connect(clientId.c_str())) {
      Serial.println("Connected to EMQX Broker!");
    } else {
      Serial.print("Failed, rc=");
      Serial.print(client.state());
      Serial.println(" trying again in 5 seconds");
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  
  // Activate the internal pull-up resistor. 
  // The pin reads HIGH normally, and drops to LOW when the button is pressed.
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  
  setup_wifi();
  client.setServer(mqtt_server, 1883);
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  // Read the physical button state
  int buttonState = digitalRead(BUTTON_PIN);

  // If the button is pressed (LOW) AND the debounce timer has passed
  if (buttonState == LOW && (millis() - lastDebounceTime) > debounceDelay) {
    Serial.println("🚨 Bathroom Button Pressed! Firing Alert...");
    
    // Publish the exact "FALL" payload to your FADE app topic
    client.publish("fade_project/sensors/team_alert", "PANIC");
    
    // Reset the timer so it doesn't spam the network
    lastDebounceTime = millis();
  }
}