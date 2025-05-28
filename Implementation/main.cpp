#include <ESP8266WiFi.h>
#include <WiFiServer.h>

const char* ssid = "ESP8266_AP";
const char* password = "12345678";

WiFiServer server(80); // TCP server on port 80

void setup() {
  Serial.begin(115200);

  // Set ESP8266 as Access Point
  WiFi.softAP(ssid, password);
  Serial.println("Access Point started");
  Serial.print("IP address: ");
  Serial.println(WiFi.softAPIP());

  // Start TCP server
  server.begin();
}

void loop() {
  WiFiClient client = server.available(); // Check for incoming client
  if (client) {
    Serial.println("New client connected");

    while (client.connected()) {
      if (client.available()) {
        String line = client.readStringUntil('\n');
        Serial.print("Received: ");
        Serial.println(line);
      }
    }

    client.stop();
    Serial.println("Client disconnected");
  }
}
