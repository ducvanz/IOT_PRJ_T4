/*
  NexusIoT Platform — ESP32 / Arduino Client Example
  ====================================================
  This example shows how to connect an ESP32 to NexusIoT Platform.
  It sends temperature + humidity data via HTTP POST every 5 seconds.

  Required Libraries (install via Arduino Library Manager):
    - WiFi (built-in for ESP32)
    - HTTPClient (built-in for ESP32)
    - ArduinoJson

  Configuration: fill in the #defines below.
*/

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// ── CONFIG ──────────────────────────────────────────────────────────────────
#define WIFI_SSID       "YourWiFiSSID"
#define WIFI_PASSWORD   "YourWiFiPassword"
#define PLATFORM_URL    "http://YOUR_SERVER_IP:8000"
#define DEVICE_API_KEY  "nxs_your_device_api_key_here"

// If using DHT sensor, include DHT.h library and uncomment:
// #include <DHT.h>
// #define DHTPIN 4
// #define DHTTYPE DHT22
// DHT dht(DHTPIN, DHTTYPE);

// ── SETUP ────────────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);

  // Connect WiFi
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500); Serial.print(".");
  }
  Serial.println("\nWiFi connected! IP: " + WiFi.localIP().toString());

  // Send online status to platform
  sendStatus("online");
}

// ── LOOP ─────────────────────────────────────────────────────────────────────
void loop() {
  // Read sensors (replace with actual sensor reads)
  float temperature = 22.5 + random(-10, 10) / 10.0;   // replace with dht.readTemperature()
  float humidity    = 60.0 + random(-50, 50) / 10.0;   // replace with dht.readHumidity()
  int   light       = analogRead(A0);

  // Send bulk readings
  bool ok = sendBulkData(temperature, humidity, light);
  Serial.println(ok ? "✓ Data sent" : "✗ Failed to send data");

  delay(5000);  // Send every 5 seconds
}

// ── SEND BULK DATA ────────────────────────────────────────────────────────────
bool sendBulkData(float temperature, float humidity, int light) {
  if (WiFi.status() != WL_CONNECTED) return false;

  HTTPClient http;
  http.begin(String(PLATFORM_URL) + "/api/v1/data/ingest/bulk");
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-API-Key", DEVICE_API_KEY);

  // Build JSON payload
  StaticJsonDocument<300> doc;
  JsonArray readings = doc.createNestedArray("readings");

  JsonObject t = readings.createNestedObject();
  t["field"] = "temperature"; t["value"] = temperature; t["unit"] = "°C";

  JsonObject h = readings.createNestedObject();
  h["field"] = "humidity"; h["value"] = humidity; h["unit"] = "%";

  JsonObject l = readings.createNestedObject();
  l["field"] = "light"; l["value"] = light; l["unit"] = "lux";

  String body;
  serializeJson(doc, body);

  int code = http.POST(body);
  http.end();
  return code == 201;
}

// ── SEND SINGLE READING ───────────────────────────────────────────────────────
bool sendSingleReading(const char* field, float value, const char* unit) {
  if (WiFi.status() != WL_CONNECTED) return false;

  HTTPClient http;
  http.begin(String(PLATFORM_URL) + "/api/v1/data/ingest");
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-API-Key", DEVICE_API_KEY);

  StaticJsonDocument<100> doc;
  doc["field"] = field;
  doc["value"] = value;
  doc["unit"]  = unit;

  String body;
  serializeJson(doc, body);

  int code = http.POST(body);
  http.end();
  return code == 201;
}

// ── SEND STATUS ───────────────────────────────────────────────────────────────
void sendStatus(const char* status) {
  HTTPClient http;
  // Status via MQTT would be: publish to "devices/{id}/status"
  // For simplicity here we just log it
  Serial.println(String("Status: ") + status);
}

/*
  ── MQTT ALTERNATIVE ──────────────────────────────────────────────────────────
  Instead of HTTP, you can use MQTT. Install PubSubClient library.

  #include <PubSubClient.h>
  WiFiClient espClient;
  PubSubClient mqttClient(espClient);

  mqttClient.setServer("YOUR_BROKER_IP", 1883);
  mqttClient.connect("esp32-device-id");

  // Publish data:
  String topic = "devices/YOUR_DEVICE_ID/data";
  String payload = "{\"field\":\"temperature\",\"value\":25.3,\"unit\":\"°C\"}";
  mqttClient.publish(topic.c_str(), payload.c_str());
*/
