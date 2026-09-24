#include "esp_camera.h"
#include <WiFi.h>
#include <PubSubClient.h>
#include <driver/i2s.h>

// =================== HARDWARE CONFIGURATION ===================
#define CAMERA_MODEL_FREENOVE_ESP32S3_CAM  // Keep your working camera model
#include "camera_pins.h"

// --- Microphone I2S Pins ---
#define I2S_SCK 1
#define I2S_WS 2
#define I2S_SD 42
#define I2S_PORT I2S_NUM_0

// 🚨 AUDIO THRESHOLD: Adjust this number based on how loud your room is! 
// If it triggers too easily, make this number higher (e.g., 500 or 1000).
const int32_t noiseThreshold = 250; 

// --- Motion Sensor Pin ---
const int motionSensorPin = 47;  
int motionState = LOW;

// =================== NETWORK CONFIGURATION ===================
const char* ssid = "emelin";        // <-- CHANGE THIS if needed
const char* password = "aliflamlamha"; // <-- CHANGE THIS if needed

// =================== MQTT & SENSOR CONFIGURATION ===================
const char* mqtt_server = "broker.emqx.io";
const char* mqtt_topic = "fade_project/sensors/team_alert";

WiFiClient espClient;
PubSubClient client(espClient);

unsigned long lastTriggerTime = 0;
unsigned long lastAudioTriggerTime = 0;
const unsigned long cooldownTime = 5000; // 5-second cooldown so it doesn't spam alerts

void startCameraServer();

void setup_mqtt() {
  client.setServer(mqtt_server, 1883);
}

void reconnect_mqtt() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    String clientId = "FADESensor-";
    clientId += String(random(0xffff), HEX);
    
    if (client.connect(clientId.c_str())) {
      Serial.println("connected");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  Serial.setDebugOutput(true);
  Serial.println();

  // 1. Initialize Motion Sensor
  pinMode(motionSensorPin, INPUT);
  Serial.println("Motion Sensor Initialized.");

  // 2. Initialize Camera
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.frame_size = FRAMESIZE_VGA;
  config.pixel_format = PIXFORMAT_JPEG; 
  config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
  config.fb_location = CAMERA_FB_IN_PSRAM;
  config.jpeg_quality = 15;
  config.fb_count = 1;

  if(psramFound()){
    config.jpeg_quality = 12;
    config.fb_count = 2;
    config.grab_mode = CAMERA_GRAB_LATEST;
  }

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x", err);
    return;
  }

  // 3. Initialize I2S Audio Driver (Microphone)
  i2s_config_t i2s_config = {
    .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
    .sample_rate = 16000,
    .bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT,
    .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
    .communication_format = i2s_comm_format_t(I2S_COMM_FORMAT_STAND_I2S),
    .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
    .dma_buf_count = 8,
    .dma_buf_len = 64,
    .use_apll = false,
    .tx_desc_auto_clear = false,
    .fixed_mclk = 0
  };

  i2s_pin_config_t pin_config = {
    .bck_io_num = I2S_SCK,
    .ws_io_num = I2S_WS,
    .data_out_num = I2S_PIN_NO_CHANGE,
    .data_in_num = I2S_SD
  };

  i2s_driver_install(I2S_PORT, &i2s_config, 0, NULL);
  i2s_set_pin(I2S_PORT, &pin_config);
  i2s_set_clk(I2S_PORT, 16000, I2S_BITS_PER_SAMPLE_32BIT, I2S_CHANNEL_MONO);
  Serial.println("Microphone Initialized.");

  // 4. Connect to Wi-Fi
  WiFi.begin(ssid, password);
  WiFi.setSleep(false);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected");

  // 5. Start the Web Server
  startCameraServer();
  Serial.print("Camera Ready! Use 'http://");
  Serial.print(WiFi.localIP());
  Serial.println("' to connect");

  // 6. Connect to MQTT Broker
  setup_mqtt();
}

void loop() {
  // Ensure MQTT remains connected
  if (!client.connected()) {
    reconnect_mqtt();
  }
  client.loop();

  // ==========================================
  // 1. CHECK THE MOTION SENSOR
  // ==========================================
  motionState = digitalRead(motionSensorPin);
  
  if (motionState == HIGH && (millis() - lastTriggerTime > cooldownTime)) {
    Serial.println("🚨 ALERT: Fall/Motion Detected!");
    client.publish(mqtt_topic, "FALL");
    lastTriggerTime = millis(); 
  }

  // ==========================================
  // 2. CHECK THE MICROPHONE
  // ==========================================
  int32_t sample = 0;
  size_t bytes_read;

  i2s_read(I2S_PORT, &sample, sizeof(sample), &bytes_read, portMAX_DELAY);

  if (bytes_read > 0) {
    sample = sample >> 14; // Shift to 32-bit space
    
    // Instead of drawing a graph, we check if the sound is louder than our threshold
    if (abs(sample) > noiseThreshold && (millis() - lastAudioTriggerTime > cooldownTime)) {
      Serial.println("🎤 ALERT: Loud Voice/Sound Detected!");
      client.publish(mqtt_topic, "VOICE"); // Transmits 'VOICE' payload to your Python UI!
      lastAudioTriggerTime = millis();
    }
  }

  // Small delay for system stability
  delay(10);
}